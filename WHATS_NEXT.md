# What's Next for StreamCatch

StreamCatch is evolving into a comprehensive media management platform. Following the "IMPLEMENT THESE" directive, we are setting an ambitious roadmap for v4.0 and beyond.

## 🚀 v4.0: The "Experience & Intelligence" Update

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
*   **Download Acceleration**:
    *   **Multi-threaded Downloading**: `aria2c` integration for faster downloads.
    *   **Smart Buffer Management**: Optimized memory usage.
*   **Hardware Acceleration**:
    *   **GPU Transcoding**: NVENC/AMF via FFmpeg.
    *   **GUI Rendering**: Metal/Vulkan/DX12 optimizations.
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
*   **Browser Extensions**: Chrome/Firefox integration via Native Messaging.
*   **Mobile Companion App**: Flutter mobile remote.
*   **Home Automation**: Home Assistant / MQTT support.
*   **Media Server Hooks**: Plex/Jellyfin notification triggers.

## ✅ Completed in v3.x
*   **Cloud Upload**: Google Drive (PyDrive2).
*   **Social Sharing**: Discord Rich Presence.
*   **Cross-Device Sync**: Export/Import configuration.
*   **Time Range Downloading**: Download specific sections.
*   **Regex Filtering**: Filter playlists.
*   **Custom Output Templates**: User-defined filename formats.
*   **Scheduled Downloads**: Specific time scheduling.
*   **RSS Feed Support**: Channel subscription.
*   **Dashboard Analytics**: Visual stats.
*   **Modern UI**: Flet-based interface.
