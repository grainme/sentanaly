use dotenv::dotenv;
use rdkafka::config::ClientConfig;
use rdkafka::producer::{FutureProducer, FutureRecord};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::error::Error;
use std::time::Duration;
use tokio;

#[derive(Debug, Serialize, Deserialize)]
struct RedditPost {
    title: String,
    content: String,
    timestamp: i64,
}

struct Reddit {
    client: Client,
    access_token: String,
    user_agent: String,
}

impl Reddit {
    async fn new() -> Result<Self, Box<dyn Error>> {
        println!("Initializing Reddit client...");
        dotenv().ok();

        let client = Client::new();
        let client_id =
            std::env::var("REDDIT_CLIENT_ID").map_err(|_| "REDDIT_CLIENT_ID not set")?;
        let client_secret =
            std::env::var("REDDIT_CLIENT_SECRET").map_err(|_| "REDDIT_CLIENT_SECRET not set")?;
        let user_agent =
            std::env::var("REDDIT_USER_AGENT").map_err(|_| "REDDIT_USER_AGENT not set")?;

        println!("Got environment variables, authenticating with Reddit...");

        let auth_str = format!("{}:{}", client_id, client_secret);
        let auth_header = format!(
            "Basic {}",
            base64::Engine::encode(&base64::engine::general_purpose::STANDARD, &auth_str)
        );

        println!("Requesting access token...");
        let response = client
            .post("https://www.reddit.com/api/v1/access_token")
            .header("Authorization", auth_header)
            .header("User-Agent", &user_agent)
            .form(&[("grant_type", "client_credentials")])
            .send()
            .await?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await?;
            println!("Reddit API error: {} - {}", status, text);
            return Err(format!("Reddit API error: {} - {}", status, text).into());
        }

        let json_response = response.json::<serde_json::Value>().await?;
        println!("Response from Reddit: {:?}", json_response);

        let access_token = json_response["access_token"]
            .as_str()
            .ok_or("Invalid access token")?
            .to_string();

        println!("Successfully obtained access token");

        Ok(Reddit {
            client,
            access_token,
            user_agent,
        })
    }

    async fn get_hot_posts(
        &self,
        subreddit: &str,
        limit: u32,
    ) -> Result<Vec<(String, String)>, Box<dyn Error>> {
        println!("Fetching posts from r/{}", subreddit);

        let url = format!(
            "https://oauth.reddit.com/r/{}/hot?limit={}",
            subreddit, limit
        );

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.access_token))
            .header("User-Agent", &self.user_agent)
            .send()
            .await?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await?;
            println!("Error fetching posts: {} - {}", status, text);
            return Err(format!("Failed to fetch posts: {} - {}", status, text).into());
        }

        let response_json = response.json::<serde_json::Value>().await?;

        let posts = response_json["data"]["children"]
            .as_array()
            .ok_or("Invalid response format")?
            .iter()
            .map(|post| {
                let data = &post["data"];
                let title = data["title"].as_str().unwrap_or("").to_string();
                let content = data["selftext"].as_str().unwrap_or("").to_string();
                (title, content)
            })
            .collect();

        println!("Successfully fetched {} posts", limit);
        Ok(posts)
    }
}

struct KafkaProducer {
    producer: FutureProducer,
    topic: String,
}

impl KafkaProducer {
    fn new(brokers: &str, topic: &str) -> Self {
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

    async fn send(&self, post: RedditPost) -> Result<(), Box<dyn Error>> {
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
        tokio::time::sleep(Duration::from_secs(60)).await;
    }
}
