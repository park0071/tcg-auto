"""스레드 자동 발행기.
threads/queue/*.json 중 발행 시각(publish_at, KST)이 지난 글을 스레드에 올리고
threads/posted/ 로 옮긴다. 링크는 본문이 아니라 첫 댓글(reply)로 단다.

queue 파일 형식:
{
  "publish_at": "2026-10-06T19:00:00+09:00",
  "type": "질문형",
  "text": "본문 (500자 이하)",
  "reply": "첫 댓글 (선택, 링크 등)",
  "topic_tag": "포켓몬카드" (선택)
}
"""
import json, os, sys, time, glob, shutil, datetime, urllib.parse, urllib.request

API = "https://graph.threads.net/v1.0"
TOKEN = os.environ["THREADS_TOKEN"]
KST = datetime.timezone(datetime.timedelta(hours=9))


def call(path, params, method="POST"):
    params = {**params, "access_token": TOKEN}
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    req = urllib.request.Request(url, data=data if method == "POST" else None, method=method)
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def publish(text, reply_to=None, topic_tag=None):
    p = {"media_type": "TEXT", "text": text}
    if reply_to:
        p["reply_to_id"] = reply_to
    if topic_tag:
        p["topic_tag"] = topic_tag
    container = call("me/threads", p)["id"]
    time.sleep(5)  # 컨테이너 처리 대기 (공식 권장)
    return call("me/threads_publish", {"creation_id": container})["id"]


def main():
    now = datetime.datetime.now(KST)
    os.makedirs("threads/posted", exist_ok=True)
    done = 0
    for f in sorted(glob.glob("threads/queue/*.json")):
        post = json.load(open(f, encoding="utf-8"))
        if datetime.datetime.fromisoformat(post["publish_at"]) > now:
            continue
        if len(post["text"]) > 500:
            print(f"[건너뜀] 500자 초과: {f}")
            continue
        pid = publish(post["text"], topic_tag=post.get("topic_tag"))
        if post.get("reply"):
            time.sleep(10)
            publish(post["reply"], reply_to=pid)
        post["posted_id"], post["posted_at"] = pid, now.isoformat()
        json.dump(post, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        shutil.move(f, os.path.join("threads/posted", os.path.basename(f)))
        print(f"[발행] {os.path.basename(f)} -> {pid}")
        done += 1
        if done >= 2:  # 한 번에 최대 2개 (스팸 방지)
            break
    print(f"완료: {done}개 발행")


if __name__ == "__main__":
    main()
