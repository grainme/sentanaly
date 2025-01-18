use crate::Deserialize;
use crate::Serialize;
use dotenv::dotenv;
use reqwest::Client;
use std::error::Error;

#[derive(Debug, Serialize, Deserialize)]
struct RedditPost {
    title: String,
    content: String,
    timestamp: i64,
}

pub struct Reddit {
    client: Client,
    access_token: String,
    user_agent: String,
}

impl Reddit {
    pub async fn new() -> Result<Self, Box<dyn Error>> {
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

    pub async fn get_hot_posts(
        &self,
        subreddit: &str,
        limit: u32,
        after: Option<String>, // Add this parameter
    ) -> Result<Vec<(String, String, String)>, Box<dyn Error>> {
        // Return tuple with post ID
        println!("Fetching posts from r/{}", subreddit);
        let mut url = format!(
            "https://oauth.reddit.com/r/{}/hot?limit={}",
            subreddit, limit
        );

        // Add after parameter if provided
        if let Some(after_id) = after {
            url.push_str(&format!("&after={}", after_id));
        }

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
                let fullname = data["name"].as_str().unwrap_or("").to_string(); // This is the ID we need
                (title, content, fullname)
            })
            .collect();

        Ok(posts)
    }
}
