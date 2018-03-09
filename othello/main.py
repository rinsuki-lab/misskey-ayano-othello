import threading
import json
from misskey import Misskey
from copy import deepcopy
from time import sleep
import os
client = Misskey(os.environ["ACCESS_TOKEN"])

myUserId = client.rest("i").json()["id"]

myGames = client.rest("othello/games", {"my": True}).json()

rival = {
    "b": "w",
    "w": "b"
} # 相手の石

def turn(board: list, boardSize: int, pos: int, my: str = "b"):
    """実際に置いてひっくりかえした結果を返す"""
    if board[pos] != "-":
        return board # そこには置けない
    board = deepcopy(board)
    other = rival[my] # 自分じゃないほう
    px = pos % boardSize
    py = int(pos / boardSize)
    for hx in range(3):
        hx -= 1
        for hy in range(3):
            hy -= 1
            if hy == 0 and hx == 0:
                continue
            x = px
            y = py
            board[x + (y*boardSize)] = my
            turnedBoard = deepcopy(board)
            while True:
                x += hx
                y += hy
                p = x + (y*boardSize)
                if x < 0 or y < 0 or x >= boardSize or y >= boardSize: # 場外に出ちゃった
                    break
                stone = turnedBoard[p]
                if stone == my:
                    board = turnedBoard
                    break
                elif stone == other:
                    turnedBoard[p] = my
                else:
                    break
    return board

def calc(board: list, boardSize: int, my: str = "b", isOthello = True):
    pos = -1 # 最強の手の初期値 -1の場合は置ける場所がない(=パス)を表す
    addCount = -114514 if isOthello else 114514 # 最強の手の初期値 この後の処理で導き出されるどの優先度よりも小さい/大きい必要がある(そうでないと置ける場所があるのにパスしてしまう)
    nowCount = len(list(filter(lambda x:x == my, board))) # 現時点で自分が置けている石の数
    for x in range(boardSize):
        for y in range(boardSize):
            p = x + (y * boardSize)
            if board[p] != "-": # 空き地以外には置かない
                continue
            count = len(list(filter(lambda x:x == my, turn(board, boardSize, p, my)))) - nowCount - 1
            # この時点でcountにはひっくりかえせる石の数が入っている
            if count < 1: # どれもひっくりかえせなかったのでこれはだめ
                continue
            # ここからcountを優先度として、石を置く場所によって優先度に手を加える
            count *= 10 # 取れる数を尊重
            if (x == 0 or x == (boardSize-1)) and (y == 0 or y == (boardSize - 1)):
                # 四隅は優先度+100
                count += 100
            elif ((y == 1  or y == boardSize-2) and (x < 2 or x >= boardSize-2)) or ((x == 1 or x == boardSize-2) and (y == 0 or y == boardSize-1)):
                # 四隅の隣は優先度-50
                count -= 50
            elif (x == 0) or (x == boardSize-1) or (y == 0) or (y == boardSize-1):
                # はしっこってなんか強そうなので優先度+3
                count += 3
            else:
                # 真ん中のほうによってほしいので真ん中のほうが優先度が高いようにする
                count += int((abs((boardSize/2) - x) + abs((boardSize/2) - y)) / 2)
            # 最後に、今計算した優先度が今まで計算した中で一番大きかったやつより大きかったら(ロセオの場合は逆)そいつを最強の手扱いにする
            if addCount < count if isOthello else addCount > count:
                pos = p
                addCount = count
    print(addCount)
    return pos # 最強の手の場所を返す

def newGame(game: dict):
    stream = client.stream("othello-game", {"game": game["id"]})
    if not game["is_started"]:
        print("wait...")
        sleep(1) # ちょっと待たないと相手に反映されないっぽいので
        stream.send(json.dumps({"type": "accept"}))
        recvType = ""
        recv = None
        while recvType != "started":
            recv = json.loads(stream.recv())
            recvType = recv.get("type")
        game = recv.get("body", game)
    board = list(game["settings"]["map"]["data"])
    boardSize = int(game["settings"]["map"]["size"])

    blackUser = game["user"+str(game["black"])+"_id"]
    myturn = "b" if blackUser == myUserId else "w"
    nowturn = "b"

    for log in game["logs"]:
        board = turn(board, boardSize, log["pos"], log["color"][0])
        nowturn = rival[log["color"][0]]
    if calc(board, boardSize, nowturn) == -1:
        print("nowturn skipped")
        nowturn = rival[nowturn]

    print(myturn, nowturn)

    a = []
    for i in range(0, len(board), boardSize):
        a.append("".join(board[i:boardSize + i]))
    print("\n".join(a))

    isOthello = not game["settings"]["is_llotheo"]

    if nowturn == myturn:
        p = calc(board, boardSize, myturn, isOthello)
        if p >= 0:
            stream.send(json.dumps({"type": "set", "pos": p}))
    while True:
        r = json.loads(stream.recv())
        if r["type"] == "set":
            body = r["body"]
            board = turn(board, boardSize, body["pos"], body["color"][0])
            nowturn = rival[body["color"][0]]
            if calc(board, boardSize, nowturn, isOthello) == -1:
                nowturn = rival[nowturn]
            if nowturn == myturn:
                p = calc(board, boardSize, myturn, isOthello)
                if p >= 0:
                    stream.send(json.dumps({"type": "set", "pos": p}))


for game in myGames:
    if game["is_ended"]: # もし終了済みだったら
        continue # しらね
    task = threading.Thread(target=newGame, args=(game,))
    task.start()
    print(game)

stream = client.stream("othello")
while True:
    r = json.loads(stream.recv())
    t = r["type"]
    if t == "invited":
        game = client.rest("othello/match", {"user_id": r["body"]["parent_id"]}).json()
        task = threading.Thread(target=newGame, args=(game,))
        task.start()