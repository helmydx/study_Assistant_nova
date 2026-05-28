import os
import glob

def get_system_stats() -> str:
    stats = {}
    
    # 1. CPU Usage (using /proc/loadavg)
    try:
        with open("/proc/loadavg", "r") as f:
            load = f.read().split()
            stats['cpu_load_1m'] = load[0]
            stats['cpu_load_5m'] = load[1]
            stats['cpu_load_15m'] = load[2]
    except Exception:
        stats['cpu_load_1m'] = "N/A"
        
    # 2. RAM Usage (using /proc/meminfo)
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    name = parts[0].strip()
                    val = parts[1].replace("kB", "").strip()
                    meminfo[name] = int(val)
                    
        total = meminfo.get("MemTotal", 0)
        free = meminfo.get("MemFree", 0)
        buffers = meminfo.get("Buffers", 0)
        cached = meminfo.get("Cached", 0)
        
        # In Linux, actual free memory includes buffers and cache
        available = free + buffers + cached
        used = total - available
        
        used_gb = used / (1024 * 1024)
        total_gb = total / (1024 * 1024)
        used_percent = (used / total) * 100 if total > 0 else 0
        
        stats['ram'] = f"{used_gb:.1f} GB / {total_gb:.1f} GB ({used_percent:.1f}%)"
    except Exception as e:
        stats['ram'] = f"Error: {str(e)}"
        
    # 3. Battery (using /sys/class/power_supply/BAT*/capacity)
    try:
        # Find any battery folders
        bat_paths = glob.glob("/sys/class/power_supply/BAT*")
        if bat_paths:
            bat_path = bat_paths[0]
            with open(os.path.join(bat_path, "capacity"), "r") as f:
                cap = f.read().strip()
            with open(os.path.join(bat_path, "status"), "r") as f:
                status = f.read().strip()
            stats['battery'] = f"{cap}% ({status})"
        else:
            stats['battery'] = "Tidak ada baterai (Desktop PC/Raspberry Pi)"
    except Exception:
        stats['battery'] = "Error reading battery status"
        
    return f"CPU Load (1m): {stats['cpu_load_1m']} | RAM: {stats['ram']} | Baterai: {stats['battery']}"

if __name__ == "__main__":
    print(get_system_stats())
