<img src="https://github.com/auerth/timelinetracker/blob/main/icon.png" width="250">
# TimelineTracker

**An open-source tool for automatically tracking your PC activities and seamlessly assigning time to your projects.**

TimelineTracker is a Windows desktop application that runs in the background and records the active window every 5 minutes. The collected data is displayed in a visual timeline, allowing you to easily and efficiently log your time to tasks in your project management tool (e.g., Redmine, Jira).

---

## ✨ Features

* **Automatic Time Tracking**: Continuously records application usage and window titles in 5-minute intervals.
* **Visual Timeline**: Two parallel timelines provide a clear overview of automatically tracked activities and manually assigned time blocks.
* **Manual Assignment via Drag & Drop**: Create and log time blocks easily by dragging with the mouse.
* **Flexible API Integration**: Connect the tracker to virtually any project management tool with a simple JSON configuration and REST API.
* **Smart Task Search**: Search for tasks directly within the app to log time correctly.
* **Open Source**: The full source code is freely available. Customize the tracker to your needs or help improve it!

---

## 🚀 Getting Started

Follow these steps to install and use TimelineTracker.

### 1. Installation

1.  Download the latest installer (`TimelineTracker.exe`) from the [Releases page](https://github.com/softwelop/timelinetracker/releases).
2.  Run the downloaded `.exe` file and follow the instructions in the installation wizard.
3.  After installation, the application starts automatically. You will find it as an icon in your taskbar.

### 2. Configuration

On first start, a configuration file `api_config.json` is automatically created in your user directory.

* **Path**: `C:\Users\YOUR_USERNAME\TimelineTracker\api_config.json`
* You can also open this folder directly via the settings menu (⚙️) in the app.

Edit this file to connect TimelineTracker to your project management tool. A detailed explanation of the configuration is provided below.

---

## ⚙️ The `api_config.json` Configuration

This file is the core of integration with external systems. Here you define how the tracker communicates with your project management tool's API.

### Example (`api_config.json`)

```json
{
  "api_base_url": "[https://your-system.com/]",
  "api_headers": {
    "Content-Type": "application/json",
    "X-Redmine-API-Key": "YOUR_API_KEY"
  },
  "endpoints": {
    "log_time": {
      "method": "POST",
      "path": "time_entries.json",
      "body": {
        "time_entry": {
          "issue_id": "{issue_id}",
          "hours": "{time_decimal}",
          "comments": "{comment}"
        }
      },
      "response_mapping": {
        "results_path": "time_entry",
        "id_field": "id"
      }
    },
    "search_issue": {
      "method": "GET",
      "path": "issues.json",
      "params": {
        "subject": "~{query}"
      },
      "response_mapping": {
        "results_path": "issues",
        "display_field": "subject",
        "id_field": "id"
      }
    },
    "delete_time_entry": {
      "method": "DELETE",
      "path": "time_entries/{time_entry_id}.json"
    }
  }
}
```

### Field Explanation

* `api_base_url`: The base URL of your API (e.g., `https://redmine.softwelop.com/`).
* `api_headers`: An object for HTTP headers. Typically includes your API key or an authentication token.
* `endpoints`: Defines the three actions the tracker can perform:
    * `log_time`: Log time.
    * `search_issue`: Search for a task.
    * `delete_time_entry`: Delete a time entry.
* **Parameters within an endpoint**:
    * `method`: The HTTP method (`GET`, `POST`, `DELETE`).
    * `path`: The API path appended to the `api_base_url`. Placeholders like `{time_entry_id}` are replaced automatically.
    * `body`: The JSON structure for `POST` requests. Placeholders `{issue_id}`, `{time_decimal}`, and `{comment}` are filled by the tracker.
    * `params`: URL parameters for `GET` requests. `{query}` is replaced with the search input.
    * `response_mapping`: Defines how the API response is interpreted.
        * `results_path`: Path to the array of results (e.g., `issues`).
        * `display_field`: Field displayed in the search list (e.g., `subject`).
        * `id_field`: Field containing the unique ID of an entry.

---

## 🛠️ Build Process (for Developers)

To build the application from source, you need Python and the packages listed in `requirements.txt` (if available).

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Create executable**:
    Run the `build.bat` file. It uses `PyInstaller` to create a single `.exe` in the `dist` folder and copies all necessary additional files (icons, example config).
3.  **Create installer**:
    * Install [Inno Setup](https://jrsoftware.org/isinfo.php).
    * Open `installer/installer_project.iss` in Inno Setup.
    * Adjust the paths in the `[Files]` section to point to the files in your `dist` folder.
    * Compile the script in Inno Setup to produce the `TimelineTracker.exe` installer.

---

## 🤝 Contributing

Contributions are welcome! If you find a bug or want to suggest a feature, please create an [issue](https://github.com/softwelop/timelinetracker/issues). To contribute code, fork the repository and submit a pull request.

---

## 📄 License & Usage

TimelineTracker is free and may be used, modified, and redistributed.

The only condition is **crediting the original author** (softwelop - Thorben Auer) in derivative works or redistribution.

**What does "credit" mean?** When using the code in your own project, please mention the origin – for example, in your README, in your app credits, or in your code comments.
