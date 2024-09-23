import platform
import psutil


def get_system_stats():
    # Retrieve system information
    cpu_percent = psutil.cpu_percent()  # CPU usage as a percentage
    memory_info = psutil.virtual_memory()  # Memory usage information
    network_info = psutil.net_io_counters()  # Network usage information


    # Format the output
    system_stats = {
        "Platform": platform.platform(),
        "CPU Usage (%)": cpu_percent,
        "Memory Usage (%)": memory_info.percent,
        "Network Usage (Bytes)": {
            "Bytes Sent": network_info.bytes_sent,
            "Bytes Received": network_info.bytes_recv
        }
    }

    return system_stats

print(get_system_stats())