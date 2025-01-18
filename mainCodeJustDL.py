import numpy as np
import pandas as pd
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
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
        texts = df['Text'].apply(self.clean_text)
        
        # Convert labels from [-1, 0, 1] to [0, 1, 2]
        labels = df['Label'].apply(lambda x: int(x + 1))
        
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

def main():
    print("Loading data...")
    df = pd.read_csv('Reddit_Data.csv')
    
    print("Initializing classifier...")
    classifier = RedditSentimentClassifier(
        max_words=50000,
        max_len=200,
        embedding_dim=200
    )
    
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
    test_data = [
        # Test Case 1: Basic functionality test
        "I love this product!",  # Positive sentiment
        "I hate this movie.",  # Negative sentiment
        "This is a great day!",  # Positive sentiment
        "It's okay, nothing special.",  # Neutral sentiment
         
        
        # Test Case 3: Real-world scenario (from social media)
        "This is the worst customer service experience ever! #badservice",  # Negative sentiment
        "Totally recommend this laptop, it's the best investment! #bestpurchase",  # Positive sentiment
        
        # Test Case 4: Text with emojis and symbols
        "I am so happy today! 😁😊",  # Positive sentiment
        "This place is terrible 😡👎",  # Negative sentiment
]
    preprocessed_data = [classifier.clean_text(text) for text in test_data] 


# Preprocess and test predictions
    sequences = classifier.tokenizer.texts_to_sequences(preprocessed_data)
    padded_sequences = pad_sequences(sequences, maxlen=classifier.max_len, padding='post', truncating='post')
    
    # Print the results
    for i, text in zip(padded_sequences, preprocessed_data):
        print(f"Original Text: {text}")
        prediction = classifier.model.predict(np.array([i]))   
        predicted_label = np.argmax(prediction, axis=1)
        print(f"Predicted Label: {predicted_label[0]} ({'Positive' if predicted_label == 2 else 'Negative' if predicted_label == 0 else 'Neutral'})\n")

main()