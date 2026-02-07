# What's Next for StreamCatch

StreamCatch is evolving into a comprehensive media management platform. We have recently completed a major overhaul to include IDM-like features, generic file support, and enhanced UI.

## 🚀 v5.0: The "Intelligence & Ecosystem" Update

### 1. User Experience (UX) & Accessibility
*   **Voice Control**: Integration with SpeechRecognition for voice commands.
*   **Adaptive Interface**:
    *   **TV Mode**: 10-foot UI for HTPCs.
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
*   **Content Recommendations**: Suggestions based on history.
*   **Sentiment Analysis**: Analyze comment sentiment.
*   **Auto-Categorization**: Organize into folders (Music, Tech, Gaming).

### 4. Integrations & Ecosystem
*   **Mobile Companion App**: Enhanced mobile remote features.
*   **Home Automation**: Home Assistant / MQTT support.
*   **Media Server Hooks**: Plex/Jellyfin notification triggers.

## ✅ Completed in v4.0 (Current)
*   **Accessibility First**:
    *   **High Contrast Mode**: Dedicated theme for visually impaired users.
    *   **Tooltips**: Enhanced accessibility with descriptive tooltips for controls.
*   **Adaptive Interface**:
    *   **Compact Mode**: "Widget" style floating window with responsive layout.
*   **Natural Language Input**: Type commands or search queries directly into the input field (e.g. "funny cats") to search YouTube.
*   **Smart Auto-Tagging**:
    *   **Keyword Detection**: Automatically tags downloads based on title and uploader (Music, Gaming, Tech, etc.).
*   **Enhanced Testing**:
    *   **Comprehensive Coverage**: Significantly expanded test suite covering core components, UI, and synchronization logic.
*   **Documentation**:
    *   **Centralized Docs**: Moved all documentation to `wiki/` for better organization.

## ✅ Completed in v3.5
*   **Refactored Architecture**:
    *   **Modular Codebase**: Separated State, Tasks, and UI logic for better maintainability.
    *   **New Branding**: "Linear Velocity" logo design.
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
