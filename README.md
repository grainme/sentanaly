# sentanaly

## First Part (kafka + reddit) Setup:
## quick setup

### 1. install stuff
```bash
# install rust (requirement to run the code)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# install docker (in case you don't have it already)
sudo apt update
sudo apt install docker.io docker-compose
```

### 2. get reddit api access
- go to https://www.reddit.com/prefs/apps
- click "create another app"
- select "script"
- fill name and description
- save the client id and secret

### 3. setup project
```bash
# edit with your reddit details
open .env and edit it
```

put this in .env (create your own app on reddit (API doc page, see step 2) - if needed :
```env
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here
REDDIT_USER_AGENT="linux:my_app:v1.0.0 (by /u/your_username)"
```

### 4. start kafka (docker file is included in the project, but why? to avoid installing kafka...)
```bash
docker-compose up -d
```

### 5. run the app
need two terminals (you can also use tmux as an alternative but two terminals is easier!)

terminal 1 - get reddit posts:
```bash
cargo run --bin reddit_stream
```

terminal 2 - see the messages (consumer, just to test whether the topic has smtg or not!):
```bash
cargo run --bin consumer
```
