# 📁 Folder Synchronization System

Advanced Python tool for synchronizing two folders using **multithreading** and **multiprocessing** for optimal performance.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 🎯 Overview

This project implements a high-performance folder synchronization system that intelligently uses:
- **Multithreading** for I/O-intensive operations (file copying/deletion)
- **Multiprocessing** for CPU-intensive operations (MD5 hash computation)

The tool ensures data integrity while maintaining excellent performance through parallel processing.

## ✨ Features

- 🔄 **Two Sync Modes:**
  - Fast mode: timestamp-based comparison
  - Secure mode: MD5 hash verification for file integrity
  
- ⚡ **Parallel Processing:**
  - Multithreading for file I/O operations
  - Multiprocessing for hash computation (utilizes all CPU cores)
  
- 📊 **Comprehensive Statistics:**
  - Files copied/deleted counters
  - Execution time tracking
  - Detailed error reporting
  
- 🛡️ **Robust Error Handling:**
  - Graceful failure management
  - Detailed error logging
  - Operation continues on individual file failures

## 🏗️ Architecture

```
FolderSynchronizer (OOP Class)
├── Phase 1: Scan & Identify files to sync
│   ├── trova_file_da_sincronizzare()
│   └── verifica_con_hash() [Multiprocessing]
│
├── Phase 2: Copy files [Multithreading]
│   └── copia_file()
│
└── Phase 3: Delete obsolete files [Multithreading]
    └── elimina_file()
```

## 🚀 Usage

### Basic Usage

```python
from pathlib import Path
from folder_sync import FolderSynchronizer

# Define source and destination folders
source = Path("./source_folder")
destination = Path("./destination_folder")

# Create synchronizer instance
syncer = FolderSynchronizer(
    source=source,
    destination=destination,
    workers=4,        # Number of parallel threads/processes
    use_hash=False    # Fast mode (timestamp-based)
)

# Run synchronization
syncer.sync()
```

### Secure Mode (with MD5 Hash)

```python
syncer = FolderSynchronizer(
    source=source,
    destination=destination,
    workers=4,
    use_hash=True    # Secure mode (hash verification)
)
syncer.sync()
```

## 📦 Installation

### Requirements

```bash
Python 3.8+
```

No external dependencies required - uses only Python standard library:
- `os`, `shutil`, `hashlib`, `pathlib`
- `concurrent.futures`, `multiprocessing`

### Clone and Run

```bash
git clone https://github.com/Murri-Hub/folder-synchronizer.git
cd folder-synchronizer
python folder_sync.py
```

## 🔧 Configuration

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | Path | required | Source folder path |
| `destination` | Path | required | Destination folder path |
| `workers` | int | 4 | Number of parallel workers |
| `use_hash` | bool | False | Enable MD5 hash verification |

### Performance Tuning

- **Workers:** Adjust based on your system (typically 4-8 for most machines)
- **Fast mode:** Best for frequent syncs, lower CPU usage
- **Secure mode:** Best for critical data, ensures 100% integrity

## 📊 Performance

### Benchmarks (example on ~1000 files, ~2GB)

| Mode | Time | CPU Usage |
|------|------|-----------|
| Fast (timestamp) | ~5 seconds | Low |
| Secure (MD5 hash) | ~15 seconds | High (all cores) |

*Performance varies based on file size, quantity, and hardware*

## 🧪 Technical Details

### Multithreading vs Multiprocessing

**Why use both?**

- **Multithreading** (`ThreadPoolExecutor`):
  - Used for **I/O-bound** operations (reading/writing files)
  - Python GIL doesn't impact I/O operations
  - Excellent for file copying and deletion

- **Multiprocessing** (`ProcessPoolExecutor`):
  - Used for **CPU-bound** operations (hash calculation)
  - Bypasses Python GIL limitation
  - Utilizes all available CPU cores (`cpu_count()`)

### Hash Calculation

- Algorithm: **MD5** (fast, sufficient for file comparison)
- Chunk size: **1MB** (balances memory usage and speed)
- Parallel processing: **All CPU cores** for maximum throughput

## 📝 Code Structure

```
folder_sync.py (~450 lines)
├── Class: FolderSynchronizer
│   ├── __init__: Configuration
│   ├── calcola_hash: MD5 computation [Multiprocessing]
│   ├── copia_file: File copying [Multithreading]
│   ├── elimina_file: File deletion [Multithreading]
│   ├── trova_file_da_sincronizzare: Scan phase
│   ├── verifica_con_hash: Hash verification [Multiprocessing]
│   ├── trova_file_da_eliminare: Identify obsolete files
│   └── sync: Main orchestration method
│
└── main: CLI interface
```

## 🎓 Learning Outcomes

This project demonstrates proficiency in:
- **Advanced Python:** OOP, context managers, pathlib
- **Concurrent Programming:** Threading and multiprocessing
- **Performance Optimization:** Parallel I/O and CPU operations
- **Error Handling:** Robust exception management
- **Code Documentation:** Comprehensive comments (Italian)

## 📄 License

MIT License - feel free to use and modify

## 👤 Author

**[Stefano Murrighile]**
- LinkedIn: [http://www.linkedin.com/in/stefano-murrighile]
- Email: [stefano.murrighile@gmail.com]

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📌 Future Improvements

- [ ] Add GUI interface
- [ ] Support for remote folders (FTP/SFTP)
- [ ] Incremental backup mode
- [ ] Scheduling/automation features
- [ ] Progress bar for large operations
- [ ] Configuration file support (YAML/JSON)

---

**⭐ If you find this project useful, please consider giving it a star!**
