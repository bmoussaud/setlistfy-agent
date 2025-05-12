# 🎵 Enhanced Setlist Agent with Spotify OAuth

Welcome to the Enhanced Setlist Agent! This intelligent music assistant combines setlist data from Setlist.fm with Spotify's powerful music platform, offering both public music search and personalized features through OAuth authentication.

## 🚀 Quick Start

### Basic Usage (No Authentication Required)

- **"Tell me about Radiohead's recent setlists"** - Get concert and setlist information
- **"Find songs similar to Bohemian Rhapsody"** - Search public music data
- **"What venues has Taylor Swift played at?"** - Venue and concert information

### Personalized Features (Requires Spotify Login)

- **"Show me my recently played tracks"** - Access your listening history
- **"What's in my Discover Weekly?"** - View your personal playlists
- **"What am I listening to right now?"** - Current playback status

## 🔐 Connect Your Spotify Account

To unlock personalized features, connect your Spotify account:

1. Type `/spotify_login` in the chat
2. Click the authorization link
3. Login to Spotify and authorize the app
4. Return to the chat - you're now connected!

## 📋 Available Commands

- `/spotify_login` - Connect your Spotify account for personalized features
- `/spotify_logout` - Disconnect from Spotify
- `/spotify_profile` - View your Spotify profile information
- `/help` - Show detailed help and command list

## 🎯 What I Can Do

### 🎤 Setlist & Concert Information (via Setlist.fm)

- Search for artist setlists and concert history
- Find venue information and concert details
- Discover what songs artists are playing live
- Track tour information and dates

### 🎶 Spotify Integration

**Public Features (No login required):**

- Search for artists, tracks, and albums
- Get artist information and top tracks
- Access public playlists
- Music recommendations

**Personal Features (Spotify login required):**

- Access your personal playlists
- View saved tracks and albums
- See your listening history
- Get currently playing track information
- Access personalized recommendations

### 🤖 Intelligent Assistance

- Natural language queries about music
- Cross-reference setlist data with Spotify tracks
- Personalized recommendations based on your taste
- Concert discovery based on your music preferences

## 🔒 Privacy & Security

- Your Spotify data is only accessed during active chat sessions
- No data is permanently stored on our servers
- You can disconnect your account at any time with `/spotify_logout`
- Only necessary permissions are requested (see OAuth guide for details)

## 💡 Pro Tips

- **Be specific**: "Show me Radiohead's 2023 setlists" works better than "Radiohead concerts"
- **Try combinations**: "Find me concerts where bands played songs from my liked tracks"
- **Use commands**: Type `/` to see available commands
- **Stay connected**: Keep your Spotify connection active for the best personalized experience

## 🛠 Technical Details

This agent uses:

- **Semantic Kernel** for intelligent orchestration
- **Setlist.fm MCP Server** for concert data
- **Spotify MCP Server** for music data
- **OAuth 2.0** for secure Spotify authentication
- **Azure AI** for natural language understanding

---

_Ready to explore music like never before? Start by asking me about your favorite artist or type `/spotify_login` to unlock personalized features!_
