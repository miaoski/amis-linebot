阿美語萌典 BOT
==============
隨手紀錄一下在新的 DigtalOcean Droplet 上安裝阿美語萌典 line bot 。

Line Bot 的 callback URL 需要 https ，會驗證簽章，有幾種方法。感謝 Ronny Wang 提供方法和幫忙測試。

舊的 Linebot 是自己刻的，新的改用 [line-bot-sdk](https://github.com/line/line-bot-sdk-python) 。


關於SSL
-------
1. 用 Heroku 做一個小的 reverse proxy。請參考 Ronny Wang 寫的 `amis-proxy.php`。如果每天用量在 18 小時以內免費，超過的話每月 US$7
2. 用 AWS CloudFront，收費是 US$0.14/GB
3. LINE 目前支援 Let's Encrypt X1 及 Let's Encrypt X3 。
4. 可以使用榮尼王的新服務 [middle2.com](middle2.com) 內建提供 SSL 及定時更新服務。


FB Messenger Bot
----------------

**FB Messenger Bot 已經放棄了** 。要做出讓 Facebook 買單的申請單有點小困難，就不想管它了。

阿美語 LineBot 和 FB Messenger Bot 使用相同的後端，只有 API 稍做修改，所以把兩個 BOT 放在同一個 repo 裡面。

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

Line BOT 的寫作參考了這篇文章:
* http://qiita.com/shikajiro/items/329d660f1a457676c450


設定檔
======
請參考 `linebot.cfg.default` 裡面的說明，修改 `linebot.cfg` 即可。

此外， `fbbot.cfg` 請放上兩行字，第一行是 Verify Token 第二行是 Page Access Token。

建議不要用 root 執行 Bot，請修改 `/etc/ufw/before.rules` 並加上 port-forwarding:

```
*nat
:PREROUTING ACCEPT [0:0]
-A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 8443 
COMMIT
```

預設的 callback URL 是 https://amis.miaoski.idv.tw:443/callback ，要修改的話請記得改一下 `linebot.py` 裡的路徑。



蔡中涵委員阿美語詞典
--------------------
請從 [amis-safolu](https://github.com/miaoski/amis-safolu/) 下載字典檔，並 `ln -s ../amis-safolu/txt/dict-amis.json dict-safolu.json` 。


詞幹表
------
從阿美語萌典的 [詞幹表](https://raw.githubusercontent.com/g0v/amis-moedict/master/amis-deploy/s/stem-words.json) 抓出來用即可。


致謝
====
LineBot 測試過程，感謝 RonnyWang 提供 Heroku PHP 轉址程式及幫忙測試憑證，感謝 Pichu Chen 提供 www.tih.tw 幫忙轉址，感謝 LINE 台灣工程師 Shawn 測試及除錯。

Facebook Messenger Bot 感謝以下測試人員:
* Lafin Miku
* Weiting Tsai
* Anthony Liu
* Yenwen Chen

LICENSE
=======
程式是 MIT License, 但阿美語萌典的資料請依循各該版權宣告。
