use dotenv::dotenv;
use reddit_stream::{kafka::KafkaProducer, reddit::Reddit, RedditPost};
use std::error::Error;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    println!("Starting Reddit streaming service...");
    println!("Checking environment variables...");

    // Verify environment variables are set
    dotenv().ok();
    if std::env::var("REDDIT_CLIENT_ID").is_err() {
        println!("Error: REDDIT_CLIENT_ID not set");
        return Err("REDDIT_CLIENT_ID not set".into());
    }
    if std::env::var("REDDIT_CLIENT_SECRET").is_err() {
        println!("Error: REDDIT_CLIENT_SECRET not set");
        return Err("REDDIT_CLIENT_SECRET not set".into());
    }
    if std::env::var("REDDIT_USER_AGENT").is_err() {
        println!("Error: REDDIT_USER_AGENT not set");
        return Err("REDDIT_USER_AGENT not set".into());
    }

    println!("Initializing components...");
    let reddit = Reddit::new().await?;
    let producer = KafkaProducer::new("localhost:9092", "reddit_posts");

    println!("Starting main loop...");
    loop {
        match reddit.get_hot_posts("rust", 25).await {
            Ok(posts) => {
                println!("Successfully fetched {} posts", posts.len());
                for (title, content) in posts {
                    let post = RedditPost {
                        title: title.clone(),
                        content,
                        timestamp: chrono::Utc::now().timestamp(),
                    };

                    match producer.send(post).await {
                        Ok(_) => println!("Successfully sent post: {}", title),
                        Err(e) => eprintln!("Failed to send post to Kafka: {}", e),
                    }
                }
            }
            Err(e) => eprintln!("Error fetching posts: {}", e),
        }

        println!("Waiting 60 seconds before next fetch...");
        tokio::time::sleep(std::time::Duration::from_secs(60)).await;
    }
}
