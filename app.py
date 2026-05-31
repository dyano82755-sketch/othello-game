import chainlit as cl
import os

def init_board():
    """盤面の初期化 (8x8) 0: 空白, 1: 黒, 2: 白"""
    board = [[0] * 8 for _ in range(8)]
    board[3][3] = 2
    board[4][4] = 2
    board[3][4] = 1
    board[4][3] = 1
    return board

def board_to_markdown(board):
    """盤面を絵文字を用いたマークダウンテキストに変換 (Canvasは使用しない)"""
    lines = ["    0  1  2  3  4  5  6  7"]
    emoji_map = {0: "🟩", 1: "⚫", 2: "⚪"}
    for i, row in enumerate(board):
        row_str = f" {i} " + "".join([emoji_map[cell] for cell in row])
        lines.append(row_str)
    return "\n".join(lines)

def get_valid_moves(board, player):
    """指定されたプレイヤーの有効な着手位置を取得"""
    valid_moves = []
    directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
    opponent = 2 if player == 1 else 1

    for r in range(8):
        for c in range(8):
            if board[r][c] != 0:
                continue
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == opponent:
                    while 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == opponent:
                        nr += dr
                        nc += dc
                    if 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == player:
                        if (r, c) not in valid_moves:
                            valid_moves.append((r, c))
                        break
    return valid_moves

def make_move(board, r, c, player):
    """石を配置し、挟まれた相手の石をひっくり返す"""
    directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
    opponent = 2 if player == 1 else 1
    board[r][c] = player

    for dr, dc in directions:
        nr, nc = r + dr, c + dc
        cells_to_flip = []
        while 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == opponent:
            cells_to_flip.append((nr, nc))
            nr += dr
            nc += dc
        if 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == player:
            for fr, fc in cells_to_flip:
                board[fr][fc] = player

def count_stones(board):
    """黒と白の石の総数をカウント"""
    black = sum(row.count(1) for row in board)
    white = sum(row.count(2) for row in board)
    return black, white

@cl.on_chat_start
async def start():
    """ゲーム開始時の初期化処理"""
    cl.user_session.set("board", init_board())
    cl.user_session.set("turn", 1)  # 1: 黒(プレイヤー), 2: 白(AI)
    await send_board_and_actions()

async def send_board_and_actions():
    """現在の盤面と、着手可能な位置をボタン(Action)として送信"""
    board = cl.user_session.get("board")
    turn = cl.user_session.get("turn")
    
    black, white = count_stones(board)
    board_md = board_to_markdown(board)
    
    status_msg = f"### 🔴 オセロゲーム\n\n**現在のスコア**\n⚫ 黒 (あなた): {black} 席\n⚪ 白 (AI): {white} 席\n\n{board_md}\n\n"
    
    valid_moves = get_valid_moves(board, turn)
    
    # プレイヤーのパス判定
    if not valid_moves:
        next_turn = 2 if turn == 1 else 1
        opp_moves = get_valid_moves(board, next_turn)
        if not opp_moves:
            # 両者打つ場所がなければゲーム終了
            winner = "引き分け"
            if black > white:
                winner = "黒(⚫)の勝ち！"
            elif white > black:
                winner = "白(⚪)の勝ち！"
            await cl.Message(content=f"{status_msg}## 🎉 ゲーム終了！\n結果: **{winner}**").send()
            return
        else:
            cl.user_session.set("turn", next_turn)
            await cl.Message(content="🛑 置ける場所がないためパスします。相手の番になります。").send()
            await send_board_and_actions()
            return

    # プレイヤーのターン（黒）
    if turn == 1:
        status_msg += "次は **あなたの番 (⚫)** です。打つ座標を選択してください："
        actions = []
        for r, c in sorted(valid_moves):
            actions.append(
                cl.Action(name="select_move", value=f"{r},{c}", label=f"({r}, {c})")
            )
        await cl.Message(content=status_msg, actions=actions).send()
    
    # AIのターン（白）
    else:
        # 簡易的なAI：有効な手の中から最初に見つかったものを選択
        r, c = valid_moves[0]
        make_move(board, r, c, 2)
        cl.user_session.set("board", board)
        cl.user_session.set("turn", 1)
        await cl.Message(content=f"🤖 AI (⚪) が ({r}, {c}) に置きました。").send()
        await send_board_and_actions()

@cl.on_action("select_move")
async def handle_move(action):
    """ユーザーが盤面の座標ボタンをクリックした際の処理"""
    val = action.value
    try:
        r, c = map(int, val.split(","))
    except Exception:
        await cl.Message(content="⚠️ 不正な操作が検出されました。").send()
        return
        
    board = cl.user_session.get("board")
    turn = cl.user_session.get("turn")
    
    if turn != 1:
        return
        
    valid_moves = get_valid_moves(board, turn)
    if (r, c) not in valid_moves:
        await cl.Message(content="❌ そこには置けません。").send()
        return
        
    # プレイヤーの手を反映
    make_move(board, r, c, 1)
    cl.user_session.set("board", board)
    cl.user_session.set("turn", 2)  # AIのターンへ
    
    await send_board_and_actions()

@cl.on_message
async def main(message: cl.Message):
    """
    セキュリティ制限: Chainlit経由での .env ファイルへのアクセスを完全に遮断
    """
    if ".env" in message.content.lower():
        await cl.Message(content="🔒 セキュリティ上の制限：.env ファイルの参照および編集は制限されています。").send()
        return
        
    await cl.Message(content="💡 オセロは画面に表示される座標ボタンをクリックしてプレイしてください。").send()
