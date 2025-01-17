import datetime
import numpy as np
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from kafka import KafkaConsumer
from pymongo import MongoClient
import re
import string
from bs4 import BeautifulSoup
import emoji
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
import warnings

try:
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)
    print("NLTK resources downloaded successfully")
except Exception as e:
    print(f"Error downloading NLTK resources: {e}")

class RedditSentimentClassifier:
    def __init__(self, max_words=50000, max_len=200, embedding_dim=200):
        self.max_words = max_words
        self.max_len = max_len
        self.embedding_dim = embedding_dim
        self.tokenizer = Tokenizer(num_words=max_words, oov_token='<OOV>')
        self.model = None
        self.wordnet_lemmatizer = None
        try:
            self.wordnet_lemmatizer = WordNetLemmatizer()
        except Exception as e:
            print(f"Warning: Could not initialize lemmatizer: {e}")
            
    def to_lower_case(self, text):
        return text.lower()

     

    def remove_html_tags(self, text):
        try:
            if not isinstance(text, str):
                return ''
            # Check if the text looks like HTML before parsing
            if '<' in text and '>' in text:
                soup = BeautifulSoup(text, 'html.parser')
                return soup.get_text()
            return text
        except:
            return text

    def remove_urls(self, text):
        return re.sub(r'http\S+|www\S+', '', text)

    def remove_punctuation(self, text):
        punctuation = string.punctuation
        return text.translate(str.maketrans('', '', punctuation))

    def replace_chat_words(self, text):
        chat_words = {
            "AFAIK": "As Far As I Know",
            "AFK": "Away From Keyboard",
            "ASAP": "As Soon As Possible",
            "ATM": "At The Moment",
            "BRB": "Be Right Back",
            "BTW": "By The Way",
            "CU": "See You",
            "FAQ": "Frequently Asked Questions",
            "FWIW": "For What It's Worth",
            "FYI": "For Your Information",
            "GG": "Good Game",
            "GN": "Good Night",
            "IMHO": "In My Honest Opinion",
            "IMO": "In My Opinion",
            "IRL": "In Real Life",
            "LOL": "Laughing Out Loud",
            "ROFL": "Rolling On The Floor Laughing",
            "THX": "Thank You",
            "TTYL": "Talk To You Later",
            "U": "You",
            "WB": "Welcome Back",
            "WTF": "What The...",
            "ILY": "I Love You",
            "JK": "Just Kidding",
            "IDC": "I Don't Care",
        }
        words = text.split()
        for i, word in enumerate(words):
            if word.upper() in chat_words:
                words[i] = chat_words[word.upper()]
        return ' '.join(words)

    def remove_stopwords(self, text):
        try:
            stop_words = set(stopwords.words('english'))
            words = text.split()
            filtered_words = [word for word in words if word.lower() not in stop_words]
            return ' '.join(filtered_words)
        except:
            return text

    def remove_emojis(self, text):
        try:
            return emoji.demojize(text)
        except:
            return text

    def lemmatize_text(self, text):
        if self.wordnet_lemmatizer is None:
            return text
        try:
            return ' '.join([self.wordnet_lemmatizer.lemmatize(word, pos='v') for word in text.split()])
        except:
            return text

    def clean_text(self, text):
        if not isinstance(text, str):
            return ''
        try:
            text = self.remove_html_tags(text)
            text = self.remove_urls(text)
            text = self.remove_punctuation(text)
            text = self.replace_chat_words(text)
            text = self.remove_stopwords(text)
            text = self.remove_emojis(text)
            text = self.lemmatize_text(text)
            text = self.to_lower_case(text) 
            return text
        except Exception as e:
            print(f"Warning: Error in text cleaning: {e}")
            return text

    def prepare_data(self, df):
        """Prepare data for training"""
        print("Cleaning texts...")
        # Convert Spark DataFrame to pandas for text processing
        pdf = df.toPandas()
        texts = pdf['Text'].apply(self.clean_text)
        
        # Convert labels from [-1, 0, 1] to [0, 1, 2]
        labels = pdf['Label'].apply(lambda x: int(x + 1))
        
        print("Tokenizing texts...")
        self.tokenizer.fit_on_texts(texts)
        sequences = self.tokenizer.texts_to_sequences(texts)
        padded_sequences = pad_sequences(sequences, maxlen=self.max_len, padding='post', truncating='post')
        
        return padded_sequences, labels.values

    def build_model(self, num_classes=3):
        """Build LSTM model architecture"""
        self.model = Sequential([
            # Removed input_length parameter from Embedding layer
            Embedding(self.max_words, self.embedding_dim),
            LSTM(256, return_sequences=True),
            BatchNormalization(),
            Dropout(0.3),
            LSTM(128),
            BatchNormalization(),
            Dropout(0.3),
            Dense(128, activation='relu'),
            BatchNormalization(),
            Dropout(0.3),
            Dense(64, activation='relu'),
            BatchNormalization(),
            Dropout(0.3),
            Dense(num_classes, activation='softmax')
        ])
        
        optimizer = Adam(learning_rate=0.001)
        self.model.compile(
            optimizer=optimizer,
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return self.model

    def train(self, X_train, y_train, X_val, y_val, epochs=10, batch_size=64):
        """Train the model"""
        class_weights = compute_class_weight(
            'balanced',
            classes=np.unique(y_train),
            y=y_train
        )
        class_weight_dict = dict(enumerate(class_weights))
        
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=3,
                restore_best_weights=True
            ),
            ModelCheckpoint(
                'best_model.keras',  # Changed file extension to .keras
                monitor='val_accuracy',
                save_best_only=True
            )
        ]
        
        history = self.model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            class_weight=class_weight_dict,
            callbacks=callbacks
        )
        
        return history
def remove_nan_duplicates(df):
    """Remove NaN values and duplicates from a Spark DataFrame."""
    df = df.dropna() 
    return df
def create_kafka_consumer(bootstrap_servers, topic):
    """Create and return a Kafka consumer"""
    return KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        value_deserializer=lambda x: x.decode('utf-8'),
        auto_offset_reset='latest',
        enable_auto_commit=True
    )

def create_mongo_connection(uri, db_name, collection_name):
    """Create and return MongoDB client, database, and collection"""
    client = MongoClient(uri)
    db = client[db_name]
    collection = db[collection_name]
    return client, collection
def get_sentiment(text,classifier): 
    # Preprocess the text
    preprocessed_text = classifier.clean_text(text)
    
    # Convert to sequence and pad
    sequence = classifier.tokenizer.texts_to_sequences([preprocessed_text])
    padded_sequence = pad_sequences(
        sequence, 
        maxlen=classifier.max_len, 
        padding='post', 
        truncating='post'
    )
    
    # Make prediction
    prediction = classifier.model.predict(padded_sequence)
    predicted_label = np.argmax(prediction, axis=1)[0]
    
    # Convert numerical label to sentiment
    sentiment_map = {0: 'Negative', 1: 'Neutral', 2: 'Positive'}
    sentiment = sentiment_map[predicted_label]
    
    return {
        'sentiment': sentiment,
        'confidence': float(prediction[0][predicted_label]),
        'preprocessed_text': preprocessed_text
    }
def save_to_mongodb(collection, original_text, analysis_results):
    """Save the original text and analysis results to MongoDB"""
    document = {
        'original_text': original_text,
        'sentiment': analysis_results['sentiment'],
        'confidence': analysis_results['confidence'],
        'preprocessed_text': analysis_results['preprocessed_text'],
        'timestamp': datetime.utcnow()
    }
    
    return collection.insert_one(document)
def process_messages(consumer, mongo_collection, classifier): 
    print("Starting to process messages...")
    try:
        for message in consumer:
            text = message.value
            print(f"Received message: {text}")
            
            # Analyze sentiment
            analysis_results = get_sentiment(text, classifier)
            
            # Save to MongoDB
            save_to_mongodb(mongo_collection, text, analysis_results)
            
            print(f"Processed and saved message. Sentiment: {analysis_results['sentiment']}")
            
    except Exception as e:
        print(f"Error processing messages: {str(e)}")
        raise e    
def build_the_model(classifier):
    print("Initializing Spark session...")
    spark = SparkSession.builder \
        .appName("RedditSentimentAnalysis") \
        .getOrCreate()

    print("Loading data...")
    # Read CSV file using Spark
    df1 = spark.read.csv('Reddit_Data.csv', header=True, inferSchema=True)
    df2 = spark.read.csv('Twitter_Data.csv', header=True, inferSchema=True)
    df = df1.union(df2)
    df=remove_nan_duplicates(df)
    print("Initializing classifier...")
    
    
    X, y = classifier.prepare_data(df)
    
    print("Splitting data...")
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
    
    print("Building and training model...")
    classifier.build_model()
    history = classifier.train(
        X_train,
        y_train,
        X_val,
        y_val,
        epochs=15,
        batch_size=64
    )
    
    print("Evaluating model on test data...")
    test_loss, test_accuracy = classifier.model.evaluate(X_test, y_test, batch_size=64)
    print(f"Test Loss: {test_loss:.4f}, Test Accuracy: {test_accuracy:.4f}")
 
     
    spark.stop()
start=True
def main(): 
    classifier = RedditSentimentClassifier(
        max_words=50000,
        max_len=200,
        embedding_dim=200
    )
    global start
    config = {
        'kafka_bootstrap_servers': ['localhost:9092'],
        'kafka_topic': 'text_analysis',
        'mongo_uri': 'mongodb://localhost:27017/',
        'mongo_db': 'sentiment_analysis',
        'mongo_collection': 'results'
    }
    if start:
        build_the_model(classifier)
        start =False
    try:
         
        consumer = create_kafka_consumer(
            config['kafka_bootstrap_servers'],
            config['kafka_topic']
        )
        
         
        mongo_client, collection = create_mongo_connection(
            config['mongo_uri'],
            config['mongo_db'],
            config['mongo_collection']
        )
        
        
        process_messages(consumer, collection, classifier)
        
    except Exception as e:
        print(f"Error in main function: {str(e)}")
        raise e
    finally: 
        consumer.close()
        mongo_client.close()
if __name__ == "__main__":
    main()