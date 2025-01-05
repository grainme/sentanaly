use crate::RedditPost;
use rdkafka::config::ClientConfig;
use rdkafka::producer::{FutureProducer, FutureRecord};
use std::error::Error;
use std::time::Duration;

pub struct KafkaProducer {
    producer: FutureProducer,
    topic: String,
}

impl KafkaProducer {
    pub fn new(brokers: &str, topic: &str) -> Self {
        println!("Initializing Kafka producer with broker: {}", brokers);

        let producer: FutureProducer = ClientConfig::new()
            .set("bootstrap.servers", brokers)
            .set("message.timeout.ms", "5000")
            .create()
            .expect("Producer creation failed");

        println!("Kafka producer initialized successfully");

        KafkaProducer {
            producer,
            topic: topic.to_string(),
        }
    }

    pub async fn send(&self, post: RedditPost) -> Result<(), Box<dyn Error>> {
        let payload = serde_json::to_string(&post)?;
        println!("Sending post to Kafka: {}", post.title);

        self.producer
            .send(
                FutureRecord::to(&self.topic)
                    .payload(&payload)
                    .key(&post.timestamp.to_string()),
                Duration::from_secs(0),
            )
            .await
            .map_err(|e| Box::new(e.0) as Box<dyn Error>)?;

        println!("Successfully sent post to Kafka");
        Ok(())
    }
}
