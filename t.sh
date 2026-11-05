set -x
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
mkdir -p out; cd out
curl -sL -A "$UA" -H 'Accept-Language: pt-BR' "https://www.youtube.com/@LulaOficial" > canal.html
CID=$(grep -o '"externalId":"UC[^"]*"' canal.html | head -1 | cut -d'"' -f4); echo "CID=$CID" > cid.txt
grep -o '"channelId":"UC[^"]*"' canal.html | sort | uniq -c | sort -rn | head -3 >> cid.txt
curl -s -A "$UA" "https://www.youtube.com/feeds/videos.xml?channel_id=$CID" > rss.xml
for V in $(grep -o '<yt:videoId>[^<]*' rss.xml | head -4 | cut -d'>' -f2); do
  curl -sL -A "$UA" -H 'Accept-Language: pt-BR' "https://www.youtube.com/watch?v=$V" > w.html
  echo "$V isLiveNow=$(grep -o '"isLiveNow":[a-z]*' w.html|head -1) isLive=$(grep -o '"isLive":[a-z]*' w.html|head -1) live_content=$(grep -o '"isLiveContent":[a-z]*' w.html|head -1) status=$(grep -o '"status":"[A-Z_]*"' w.html|head -1) badge=$(grep -o 'BADGE_STYLE_TYPE_LIVE_NOW' w.html|head -1) thumb=$(curl -s -o /dev/null -w '%{http_code}' https://i.ytimg.com/vi/$V/hqdefault_live.jpg)" >> watch.txt
done
curl -sL -A "$UA" "https://www.youtube.com/@LulaOficial/streams" > streams.html
grep -o '"text":"AO VIVO"\|"style":"LIVE"\|BADGE_STYLE_TYPE_LIVE_NOW\|"label":"AO VIVO"' streams.html | sort | uniq -c > streams.txt
grep -o '"videoId":"[^"]*"' streams.html | head -5 >> streams.txt
rm -f canal.html w.html streams.html
