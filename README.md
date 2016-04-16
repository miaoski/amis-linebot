阿美語萌典 LINE BOT
===================
隨手紀錄一下在新的 DigtalOcean Droplet 上安裝阿美語萌典 line bot 。

Line Bot 的 callback URL 需要 https ，會驗證簽章，請愛用 Let's Encrypt。

```
apt-get update
apt-get dist-upgrade
cd /opt
apt-get install git python-pip build-essential python-dev libffi-dev libssl-dev
pip install pyopenssl ndg-httpsclient pyasn1
pip install urllib3 --upgrade
git clone https://github.com/letsencrypt/letsencrypt /opt/letsencrypt
./letsencrypt-auto --standalone -d amis.noip.me
```

改一下 default locale 
```
locale-gen zh_TW.UTF-8
vim /etc/default/locale
```

BOT 的話，參考這篇
* http://qiita.com/shikajiro/items/329d660f1a457676c450


LICENSE
=======
程式是 MIT License, 但阿美語萌典的資料請依循各該版權宣告。
