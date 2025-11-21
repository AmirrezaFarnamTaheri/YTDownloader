# What's Next for StreamCatch

StreamCatch is evolving into a comprehensive media management platform. We have recently completed a major overhaul to include IDM-like features, generic file support, and enhanced UI.

## 🚀 v4.0: The "Intelligence & Ecosystem" Update

### 1. User Experience (UX) & Accessibility
*   **Accessibility First**:
    *   **Screen Reader Support**: Semantic labels for NVDA, JAWS, and VoiceOver.
    *   **High Contrast Mode**: Dedicated theme for visually impaired users.
    *   **Keyboard Navigation**: Full keyboard support (J/K to move, D to delete, Space to pause).
*   **Voice Control**: Integration with SpeechRecognition for voice commands.
*   **Adaptive Interface**:
    *   **Compact Mode**: "Widget" style floating window.
    *   **TV Mode**: 10-foot UI for HTPCs.
*   **Natural Language Input**: Type commands like "Download the latest video from MKBHD in 1080p".
*   **Theme Store**: Community-submitted themes.

### 2. Performance & Core Engineering
*   **Browser Integration**: Chrome/Firefox extensions via Native Messaging to replace "Clipboard Monitor" with seamless "Click to Download".
*   **Mirror Search**: Automatically find alternative mirrors for generic files.
*   **P2P Support**: BitTorrent/Magnet link support (libtorrent).
*   **Distributed Processing**:
    *   **Cluster Mode**: Master/Worker node delegation on LAN.
*   **Multi-User Support**:
    *   **Profiles**: Separate histories and queues.
    *   **Role-Based Access**: Admin vs Guest.
*   **Scripting**: Lua/Python hooks for custom logic.

### 3. AI & Smart Features
*   **Video Summarization**: Local LLM integration (Llama 3, Phi-3) for summaries.
*   **Smart Auto-Tagging**: AI-based categorization and tagging.
*   **Content Recommendations**: Suggestions based on history.
*   **Sentiment Analysis**: Analyze comment sentiment.
*   **Auto-Categorization**: Organize into folders (Music, Tech, Gaming).

### 4. Integrations & Ecosystem
*   **Mobile Companion App**: Enhanced mobile remote features.
*   **Home Automation**: Home Assistant / MQTT support.
*   **Media Server Hooks**: Plex/Jellyfin notification triggers.

## ✅ Completed in v3.5 (Current)
*   **IDM-Like Features**:
    *   **Clipboard Monitor**: Auto-detect URLs.
    *   **Generic/Direct Download**: Robust file downloading support.
    *   **Force Generic Mode**: Bypass extraction for direct links.
*   **Platform Expansion**:
    *   **Twitter/X & Instagram**: First-class support.
    *   **Telegram**: Public channel scraping.
*   **UI Overhaul**:
    *   **New Aesthetics**: Indigo theme, platform icons, polished layout.
    *   **Navigation Rail**: Better hierarchy.
*   **Cloud Upload**: Google Drive (PyDrive2).
*   **Social Sharing**: Discord Rich Presence.
*   **Cross-Device Sync**: Export/Import configuration.
*   **Time Range Downloading**: Download specific sections.
*   **Regex Filtering**: Filter playlists.
*   **Custom Output Templates**: User-defined filename formats.
*   **Scheduled Downloads**: Specific time scheduling.
*   **RSS Feed Support**: Channel subscription.
*   **Dashboard Analytics**: Visual stats.
*   **Performance**: Aria2c and GPU acceleration support.
