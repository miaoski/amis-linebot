<?php
// Written by Ronny Wang
$curl = curl_init('https://amis.miaoski.idv.tw/callback');
curl_setopt($curl, CURLOPT_HTTPHEADER, array(
	'X-LINE-ChannelSignature: ' . urlencode($_SERVER['HTTP_X_LINE_CHANNELSIGNATURE']),
    'Content-type: application/json; charset=UTF-8'));
curl_setopt($curl, CURLOPT_POST, true);
curl_setopt($curl, CURLOPT_POSTFIELDS, file_get_contents("php://input"));
curl_exec($curl);
