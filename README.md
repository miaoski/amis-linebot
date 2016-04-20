阿美語萌典 BOT
==============
隨手紀錄一下在新的 DigtalOcean Droplet 上安裝阿美語萌典 line bot 。

Line Bot 的 callback URL 需要 https ，會驗證簽章，目前正在和 LINE 工程師合作處理中。

FB Messenger Bot 的前置作業，請參考 [Facebook Messenger Platform Quick Start](https://developers.facebook.com/docs/messenger-platform/quickstart) 的說明。

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


設定檔
======
請參考 `linebot.cfg.default` 裡面的說明，修改 `linebot.cfg` 即可。

此外， `fbbot.cfg` 請放上兩行字，第一行是 Verify Token 第二行是 Page Access Token。

修改 `/etc/ufw/before.rules` 並加上 port-forwarding:
```
*nat
:PREROUTING ACCEPT [0:0]
-A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 8443 
COMMIT
```

預設的 callback URL 是 https://miaoski.idv.tw:443/callback ，要修改的話請記得改一下 `linebot.py` 裡的路徑。



致謝
====
LineBot 測試過程，感謝 RonnyWang 提供 Heroku PHP 轉址程式及幫忙測試憑證，感謝 Pichu Chen 提供 www.tih.tw 幫忙轉址，感謝 LINE 台灣工程師 Shawn 測試及除錯。

Facebook Messenger Bot 感謝以下測試人員:
* Lafin Miku
* Weiting Tsai
* Anthony Liu

LICENSE
=======
程式是 MIT License, 但阿美語萌典的資料請依循各該版權宣告。
