# PySentinel - System Monitoring Tool

Clément GHANEME - 09/2024

## Overview

**PySentinel** is a comprehensive system monitoring tool designed to monitor **CPU**, **RAM**, **GPU**, and **network usage** in real-time. It supports configurable thresholds and generates alert emails when predefined limits are exceeded. The application also provides detailed resource usage graphs and email reports.

## Features

- **System Resource Monitoring**:  
  - Monitor CPU, RAM, GPU, and network activity.
  - Customizable thresholds for each monitored resource.
  
- **Real-time Graphs**:  
  - Visualize system performance and network usage with live graphs.
  
- **Email Alerts**:  
  - Configurable SMTP settings for email alerts.
  - Threshold breach alerts and daily reports sent to your inbox.
  
- **CSV Logging**:  
  - Logs data into daily CSV files for future reference.
  
- **GUI Interface**:  
  - Tkinter-based interface for user-friendly interaction.
  - Configuration options for refresh rates, thresholds, and email settings.
 
## Footnote

- **Version V038**: Drive threshold notifications were functioning correctly, but other notifications (CPU, RAM, network) were not working.
- **Version V046**: All notifications (CPU, RAM, network) are now working, but drive notifications are currently not functioning. The cause of this issue is still under investigation.

## Installation

### Clone the Repository

```bash
git clone https://github.com/your-username/PySentinel.git
cd PySentinel
