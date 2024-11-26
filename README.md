# Backend

<!-- TOC -->
- [Backend](#Backend)
    - [基本設定](#基本設定)
<!-- /TOC -->

## 基本設定
> 請先確認有安裝 Python, MySQL

設定 python 3.10 虛擬環境(conda), 請將 myenv 換成自己要的虛擬環境名稱
```
conda create -n myenv python=3.10
conda activate myenv
```

clone 此專案
```
git clone https://github.com/NTNU-SE-Alpha/backend.git
```

使用 pip 安裝所需要的 packages

```
pip install -r requirements.txt
```

將 `.env.example` 重新命名為 `.env`，並且填上正確的設定資料

執行 `init_db.py` 來初始化資料庫
```
python init_db.py
```

執行 flask server

```
flask run
```
