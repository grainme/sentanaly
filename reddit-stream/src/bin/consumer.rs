use rdkafka::config::ClientConfig;
use rdkafka::consumer::{Consumer, StreamConsumer};
use rdkafka::Message;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let consumer: StreamConsumer = ClientConfig::new()
        .set("group.id", "my_consumer_group")
        .set("bootstrap.servers", "localhost:9092")
        .set("auto.offset.reset", "earliest")
        .create()?;

    consumer.subscribe(&["reddit_posts"])?;

    println!("Starting Kafka consumer...");
    loop {
        match consumer.recv().await {
            Ok(msg) => {
                let payload = msg.payload();
                match payload {
                    Some(p) => {
                        if let Ok(content) = std::str::from_utf8(p) {
                            println!("Received message: {}", content);
                        } else {
                            println!("Error: Could not parse message as UTF-8");
                        }
                    }
                    None => println!("Empty message received"),
                }
            }
            Err(e) => println!("Error receiving message: {}", e),
        }
    }
}
