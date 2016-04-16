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
./letsencrypt-auto --standalone -d amis.miaoski.idv.tw
pip install flask
```

改一下 default locale 
```
locale-gen zh_TW.UTF-8
vim /etc/default/locale
```

BOT 的話，參考這篇
* http://qiita.com/shikajiro/items/329d660f1a457676c450


修改設定
========
請參考 `linebot.cfg.default` 裡面的說明，修改 `linebot.cfg` 即可。

修改 `/etc/ufw/before.rules` 並加上 port-forwarding:
```
*nat
:PREROUTING ACCEPT [0:0]
-A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 8443 
COMMIT
```

預設的 callback URL 是 https://miaoski.idv.tw:443/callback ，要修改的話請記得改一下 `linebot.py` 裡的路徑。


LICENSE
=======
程式是 MIT License, 但阿美語萌典的資料請依循各該版權宣告。
