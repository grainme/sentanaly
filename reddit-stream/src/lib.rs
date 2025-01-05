use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct RedditPost {
    pub title: String,
    pub content: String,
    pub timestamp: i64,
}

pub mod kafka;
pub mod reddit;
