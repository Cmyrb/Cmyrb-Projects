#!/usr/bin/env python3
"""
Cmyrb Casino
pip install pillow  then  python casino.py
"""
import sys, subprocess, traceback, json, os, datetime
def _ensure(pkg, import_as=None):
    try: __import__(import_as or pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
_ensure("pillow", "PIL")

import tkinter as tk
from tkinter import font as tkfont
import random, math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List
from PIL import Image, ImageDraw, ImageFont, ImageTk

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
CW, CH       = 90, 126
CHIP_DENOMS  = (5, 25, 50, 100, 500)
GOLD         = "#c9a84c"
DARK         = "#1a4a2e"
NAV          = "#0d2b1a"
START_BAL    = 500.0
LB_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "casino_leaderboard.json")

# ─────────────────────────────────────────────────────────────────────────────
#  LEADERBOARD  (JSON persistence)
# ─────────────────────────────────────────────────────────────────────────────
class Leaderboard:
    EMPTY = lambda: {
        "peak_balance": START_BAL,
        "biggest_win":  0.0,
        "total_rounds": 0,
        "total_won":    0.0,
        "blackjacks":   0,
        "sessions":     0,
        "last_played":  "",
    }

    def __init__(self):
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(LB_FILE):
            try:
                with open(LB_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def _save(self):
        try:
            with open(LB_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            traceback.print_exc()

    def get(self, nickname):
        return self._data.get(nickname, None)

    def update(self, nickname, session_stats: dict):
        rec = self._data.get(nickname, None)
        if rec is None:
            rec = Leaderboard.EMPTY()
            self._data[nickname] = rec
        rec["sessions"]     += 1
        rec["total_rounds"] += session_stats.get("rounds", 0)
        rec["total_won"]    += session_stats.get("net_total", 0.0)
        rec["blackjacks"]   += session_stats.get("blackjacks", 0)
        rec["last_played"]   = datetime.datetime.now().strftime("%Y-%m-%d")
        pb = session_stats.get("peak_balance", START_BAL)
        if pb > rec["peak_balance"]:
            rec["peak_balance"] = pb
        bw = session_stats.get("biggest_win", 0.0)
        if bw > rec["biggest_win"]:
            rec["biggest_win"] = bw
        rec["total_won"]    = round(rec["total_won"], 2)
        rec["peak_balance"] = round(rec["peak_balance"], 2)
        rec["biggest_win"]  = round(rec["biggest_win"], 2)
        self._save()

    def top(self, n=10, key="peak_balance"):
        rows = [(nick, rec) for nick, rec in self._data.items()]
        rows.sort(key=lambda x: x[1].get(key, 0), reverse=True)
        return rows[:n]

LEADERBOARD = Leaderboard()

# ─────────────────────────────────────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _font_pil(size, bold=False):
    paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

_SUIT_COLOR = {"♠":"#111111","♣":"#111111","♥":"#cc0000","♦":"#cc0000"}
_PIPS = {
    "A":[(1,3)], "2":[(1,1),(1,5)], "3":[(1,1),(1,3),(1,5)],
    "4":[(0,1),(2,1),(0,5),(2,5)], "5":[(0,1),(2,1),(1,3),(0,5),(2,5)],
    "6":[(0,1),(2,1),(0,3),(2,3),(0,5),(2,5)],
    "7":[(0,1),(2,1),(1,2),(0,3),(2,3),(0,5),(2,5)],
    "8":[(0,1),(2,1),(1,2),(0,3),(2,3),(1,4),(0,5),(2,5)],
    "9":[(0,1),(2,1),(0,2),(2,2),(1,3),(0,4),(2,4),(0,5),(2,5)],
    "10":[(0,1),(2,1),(1,2),(0,2),(2,2),(0,4),(2,4),(1,4),(0,5),(2,5)],
}

def _pip(draw, cx, cy, suit, color, sz=11):
    r = sz // 2
    if suit == "♥":
        draw.ellipse([cx-r,cy-r,cx,cy], fill=color)
        draw.ellipse([cx,cy-r,cx+r,cy], fill=color)
        draw.polygon([(cx-r,cy-r//2),(cx+r,cy-r//2),(cx,cy+r)], fill=color)
    elif suit == "♦":
        draw.polygon([(cx,cy-r),(cx+r,cy),(cx,cy+r),(cx-r,cy)], fill=color)
    else:
        f = _font_pil(sz+2, True)
        bb = draw.textbbox((0,0), suit, font=f)
        draw.text((cx-(bb[2]-bb[0])//2, cy-(bb[3]-bb[1])//2), suit, fill=color, font=f)

def make_card_image(rank, suit):
    color = _SUIT_COLOR[suit]
    img = Image.new("RGBA", (CW,CH), (255,255,255,255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0,0,CW-1,CH-1], radius=8, fill="white", outline="#aaaaaa", width=1)
    fr = _font_pil(15, True); fs = _font_pil(11)
    d.text((5,3),  rank, fill=color, font=fr)
    d.text((6,18), suit, fill=color, font=fs)
    bb = d.textbbox((0,0), rank, font=fr)
    rw, rh = bb[2]-bb[0], bb[3]-bb[1]
    d.text((CW-5-rw, CH-3-rh-13), rank, fill=color, font=fr)
    d.text((CW-6-rw+1, CH-3-rh), suit, fill=color, font=fs)
    if rank in ("J","Q","K"):
        d.rectangle([9,25,CW-10,CH-26], fill="#fdf6e3")
        fb = _font_pil(40, True)
        bb2 = d.textbbox((0,0), rank, font=fb)
        tw,th = bb2[2]-bb2[0], bb2[3]-bb2[1]
        d.text(((CW-tw)//2,(CH-th)//2-4), rank, fill=color, font=fb)
    elif rank == "A":
        _pip(d, CW//2, CH//2, suit, color, sz=32)
    else:
        cols = [18, CW//2, CW-18]
        top_y, bot_y = 32, CH-32
        rows = [top_y + i*(bot_y-top_y)//6 for i in range(7)]
        for ci,ri in _PIPS[rank]:
            _pip(d, cols[ci], rows[ri], suit, color, sz=11)
    return img

def make_back_image():
    img = Image.new("RGBA", (CW,CH), (255,255,255,255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0,0,CW-1,CH-1], radius=8, fill="#0d47a1", outline="#aaaaaa", width=1)
    for i in range(0,CW,8): d.line([(i,0),(i,CH)], fill="#1565c0", width=1)
    for j in range(0,CH,8): d.line([(0,j),(CW,j)], fill="#1565c0", width=1)
    d.rounded_rectangle([5,5,CW-6,CH-6], radius=6, outline="#1976d2", width=2)
    return img

def make_felt():
    img = Image.new("RGB", (200,200), "#1a4a2e")
    d = ImageDraw.Draw(img)
    rng = random.Random(7)
    for _ in range(5000):
        x,y = rng.randint(0,199), rng.randint(0,199)
        c = rng.randint(-18,18)
        b = [0x1a,0x4a,0x2e]
        d.point((x,y), fill=tuple(max(0,min(255,b[i]+c)) for i in range(3)))
    return img

def make_chip_image(denom, sz=46):
    COLORS = {5:"#e74c3c",25:"#27ae60",50:"#2980b9",100:"#8e44ad",500:"#c9a84c"}
    col = COLORS.get(denom, "#888")
    img = Image.new("RGBA", (sz,sz), (0,0,0,0))
    d = ImageDraw.Draw(img)
    r = sz // 2
    d.ellipse([0,0,sz-1,sz-1], fill=col, outline="white", width=2)
    d.ellipse([6,6,sz-7,sz-7], outline="white", width=1)
    for ang in range(0, 360, 30):
        rad = math.radians(ang)
        x1 = r + int((r-3)*math.cos(rad)); y1 = r + int((r-3)*math.sin(rad))
        x2 = r + int((r-8)*math.cos(rad)); y2 = r + int((r-8)*math.sin(rad))
        d.line([(x1,y1),(x2,y2)], fill="white", width=2)
    lbl = "${}".format(denom)
    f = _font_pil(max(8, sz//5), True)
    bb = d.textbbox((0,0), lbl, font=f)
    d.text((r-(bb[2]-bb[0])//2, r-(bb[3]-bb[1])//2), lbl, fill="white", font=f)
    return img

CARD_IMG: dict = {}
CHIP_IMG: dict = {}

def build_caches():
    smap = {"♠":"spades","♥":"hearts","♦":"diamonds","♣":"clubs"}
    for suit in ("♠","♥","♦","♣"):
        for rank in ("2","3","4","5","6","7","8","9","10","J","Q","K","A"):
            key = "{}_of_{}".format(rank, smap[suit])
            CARD_IMG[key] = ImageTk.PhotoImage(make_card_image(rank, suit))
    CARD_IMG["back"] = ImageTk.PhotoImage(make_back_image())
    for d in CHIP_DENOMS:
        CHIP_IMG[d] = ImageTk.PhotoImage(make_chip_image(d))

def _amount_to_chip_stack(amount):
    remaining = round(amount)
    stack = []
    for d in sorted(CHIP_DENOMS, reverse=True):
        if remaining <= 0: break
        count = remaining // d
        if count > 0:
            stack.append([d, count])
            remaining -= d * count
    if not stack:
        stack.append([5, 1])
    return stack

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SessionState:
    balance: float = START_BAL
    nickname: str  = ""
    current_game: str = ""
    _listeners: List[Callable] = field(default_factory=list, repr=False, compare=False)
    _peak_balance: float = field(default=START_BAL, repr=False, compare=False)
    _biggest_win:  float = field(default=0.0,       repr=False, compare=False)
    _total_rounds: int   = field(default=0,         repr=False, compare=False)
    _net_total:    float = field(default=0.0,       repr=False, compare=False)
    _blackjacks:   int   = field(default=0,         repr=False, compare=False)

    def add_listener(self, cb):
        if cb not in self._listeners: self._listeners.append(cb)
    def remove_listener(self, cb):
        self._listeners = [x for x in self._listeners if x is not cb]

    def update_balance(self, amount: float):
        self.balance = round(self.balance + amount, 2)
        if self.balance > self._peak_balance:
            self._peak_balance = self.balance
        for cb in list(self._listeners): cb(self.balance)

    def record_round(self, net: float, is_blackjack: bool):
        self._total_rounds += 1
        self._net_total     = round(self._net_total + net, 2)
        if net > self._biggest_win:
            self._biggest_win = net
        if is_blackjack:
            self._blackjacks += 1

    def reset_session_stats(self):
        self.balance        = START_BAL
        self._peak_balance  = START_BAL
        self._biggest_win   = 0.0
        self._total_rounds  = 0
        self._net_total     = 0.0
        self._blackjacks    = 0
        for cb in list(self._listeners): cb(self.balance)

    def session_stats_dict(self):
        return {
            "peak_balance": self._peak_balance,
            "biggest_win":  self._biggest_win,
            "rounds":       self._total_rounds,
            "net_total":    self._net_total,
            "blackjacks":   self._blackjacks,
        }

# ─────────────────────────────────────────────────────────────────────────────
#  SHOE
# ─────────────────────────────────────────────────────────────────────────────
class CutCardReached(Exception): pass

@dataclass
class Card:
    suit: str; rank: str; value: int
    def key(self):
        m = {"♠":"spades","♥":"hearts","♦":"diamonds","♣":"clubs"}
        return "{}_of_{}".format(self.rank, m[self.suit])

def _rv(r):
    if r == "A": return 11
    if r in ("J","Q","K"): return 10
    return int(r)

class Shoe:
    def __init__(self, decks=6):
        self.decks=decks; self.cards=[]; self.cut=0; self.dealt=0
        self.build()
    def build(self):
        self.cards = [
            Card(s, r, _rv(r))
            for _ in range(self.decks)
            for s in ("♠","♥","♦","♣")
            for r in ("2","3","4","5","6","7","8","9","10","J","Q","K","A")
        ]
        self.shuffle()
    def shuffle(self):
        random.shuffle(self.cards)
        n = len(self.cards)
        self.cut = random.randint(n-75, n-60)
        self.dealt = 0
    def deal_one(self):
        if not self.cards: raise CutCardReached()
        c = self.cards.pop(0)
        self.dealt += 1
        if self.dealt >= self.cut: raise CutCardReached()
        return c

# ─────────────────────────────────────────────────────────────────────────────
#  HAND
# ─────────────────────────────────────────────────────────────────────────────
class Hand:
    def __init__(self):
        self.cards = []; self._tot = None
    def add(self, c):
        self.cards.append(c); self._tot = None
    def total(self):
        if self._tot is not None: return self._tot
        s = sum(c.value for c in self.cards)
        a = sum(1 for c in self.cards if c.rank == "A")
        while s > 21 and a > 0: s -= 10; a -= 1
        self._tot = s; return s
    def is_bj(self):     return len(self.cards) == 2 and self.total() == 21
    def is_bust(self):   return self.total() > 21
    def can_split(self): return len(self.cards) == 2 and self.cards[0].rank == self.cards[1].rank
    def can_dbl(self):   return len(self.cards) == 2

# ─────────────────────────────────────────────────────────────────────────────
#  SIDE BETS
# ─────────────────────────────────────────────────────────────────────────────
def pp_result(c1, c2):
    if c1.rank != c2.rank: return ("no_win", 0)
    if c1.suit == c2.suit: return ("perfect_pair", 30)
    RED = {"♥","♦"}
    if (c1.suit in RED) == (c2.suit in RED): return ("colored_pair", 10)
    return ("mixed_pair", 5)

def t3_result(c1, c2, du):
    cards = [c1,c2,du]; ranks = [c.rank for c in cards]; suits = [c.suit for c in cards]
    ro = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
    if len(set(suits))==1 and len(set(ranks))==1: return ("suited_three_of_a_kind", 100)
    if len(set(ranks))==1:                        return ("three_of_a_kind", 30)
    vs = sorted(ro.index(r) for r in ranks)
    straight = (vs[2]-vs[0]==2 and vs[1]-vs[0]==1) or sorted(ranks)==["2","3","A"]
    flush    = len(set(suits)) == 1
    if straight and flush: return ("straight_flush", 40)
    if flush:              return ("flush", 5)
    if straight:           return ("straight", 10)
    return ("no_win", 0)

# ─────────────────────────────────────────────────────────────────────────────
#  GAME ENGINE
# ─────────────────────────────────────────────────────────────────────────────
PLAYER = "player"; DEALER = "dealer"; FAILED = "failed"

class GS(Enum):
    BETTING = auto(); PLAYER_TURN = auto(); DEALER_TURN = auto()

class BJGame:
    def __init__(self, session: SessionState):
        self.session = session; self.shoe = Shoe(6)
        self.state = GS.BETTING; self.player_hands = [Hand()]
        self.dealer_hand = Hand(); self.hand_idx = 0
        self.bet = 0.0; self.sb_amounts = {}; self.sb_results = {}
        self.reshuffle_flag = False

    def _card(self):
        try: return self.shoe.deal_one()
        except CutCardReached:
            self.reshuffle_flag = True; self.shoe.build()
            return self.shoe.deal_one()

    def active_hand(self): return self.player_hands[self.hand_idx]

    def set_bet(self, amount):
        if self.state != GS.BETTING or amount <= 0 or amount > self.session.balance: return False
        self.bet = round(amount, 2); return True

    def set_side_bet(self, kind, amount):
        if self.state != GS.BETTING or amount <= 0: return
        self.sb_amounts[kind] = round(amount, 2)

    def deal(self):
        if self.state != GS.BETTING or self.bet <= 0: return False
        cost = self.bet + sum(self.sb_amounts.values())
        if cost > self.session.balance: return False
        self.session.update_balance(-cost)
        self.player_hands = [Hand()]; self.dealer_hand = Hand()
        self.hand_idx = 0; self.sb_results = {}; self.reshuffle_flag = False
        self.player_hands[0].add(self._card()); self.dealer_hand.add(self._card())
        self.player_hands[0].add(self._card()); self.dealer_hand.add(self._card())
        p1,p2 = self.player_hands[0].cards[0], self.player_hands[0].cards[1]
        du = self.dealer_hand.cards[0]
        if "pp" in self.sb_amounts: self.sb_results["pp"] = pp_result(p1, p2)
        if "t3" in self.sb_amounts: self.sb_results["t3"] = t3_result(p1, p2, du)
        self.state = GS.PLAYER_TURN; return True

    def player_has_bj(self):
        return len(self.player_hands)==1 and self.hand_idx==0 and self.player_hands[0].is_bj()

    def hit(self):
        if self.state != GS.PLAYER_TURN: return FAILED
        self.active_hand().add(self._card())
        if self.active_hand().is_bust() or self.active_hand().total()==21: return self._advance()
        return PLAYER

    def stand(self):
        if self.state != GS.PLAYER_TURN: return FAILED
        return self._advance()

    def double_down(self):
        if self.state != GS.PLAYER_TURN:    return FAILED
        if not self.active_hand().can_dbl(): return FAILED
        if self.bet > self.session.balance:  return FAILED
        self.session.update_balance(-self.bet)
        self.bet = round(self.bet * 2, 2)
        self.active_hand().add(self._card())
        return self._advance()

    def split(self):
        if self.state != GS.PLAYER_TURN:        return FAILED
        if not self.active_hand().can_split():   return FAILED
        if self.bet > self.session.balance:      return FAILED
        self.session.update_balance(-self.bet)
        h = self.active_hand(); c2 = h.cards.pop(1); h._tot = None
        h.add(self._card())
        nh = Hand(); nh.add(c2); nh.add(self._card())
        self.player_hands.insert(self.hand_idx+1, nh)
        return PLAYER

    def _advance(self):
        self.hand_idx += 1
        if self.hand_idx >= len(self.player_hands):
            self.state = GS.DEALER_TURN; return DEALER
        return PLAYER

    def dealer_needs_hit(self):
        return self.state == GS.DEALER_TURN and self.dealer_hand.total() < 17

    def dealer_hit(self):
        if self.state == GS.DEALER_TURN: self.dealer_hand.add(self._card())

    def payout_and_reset(self):
        msgs = []; round_net = 0.0; is_bj = False
        if self.state == GS.DEALER_TURN:
            dt = self.dealer_hand.total(); dbj = self.dealer_hand.is_bj()
            for hand in self.player_hands:
                pt = hand.total(); pbj = hand.is_bj()
                if pbj and not dbj:
                    w = round(self.bet * 1.5, 2)
                    self.session.update_balance(self.bet + w)
                    msgs.append("BLACKJACK!  +${:.2f}".format(w))
                    round_net += w; is_bj = True
                elif pbj and dbj:
                    self.session.update_balance(self.bet)
                    msgs.append("PUSH")
                elif dbj:
                    msgs.append("DEALER BLACKJACK  -${:.2f}".format(self.bet))
                    round_net -= self.bet
                elif hand.is_bust():
                    msgs.append("BUST  -${:.2f}".format(self.bet))
                    round_net -= self.bet
                elif dt > 21 or pt > dt:
                    self.session.update_balance(self.bet * 2)
                    msgs.append("WIN  +${:.2f}".format(self.bet))
                    round_net += self.bet
                elif pt == dt:
                    self.session.update_balance(self.bet)
                    msgs.append("PUSH")
                else:
                    msgs.append("LOSE  -${:.2f}".format(self.bet))
                    round_net -= self.bet
            for kind, (name, mult) in self.sb_results.items():
                amt = self.sb_amounts.get(kind, 0)
                if mult > 0:
                    self.session.update_balance(amt * (mult+1))
                    msgs.append("{}  +${:.2f}".format(name.replace("_"," ").title(), amt*mult))
                    round_net += amt * mult
        result = " | ".join(msgs) if msgs else "Round over"
        carry  = min(self.bet, self.session.balance)
        self.player_hands = [Hand()]; self.dealer_hand = Hand()
        self.hand_idx = 0; self.sb_results = {}; self.sb_amounts = {}
        self.bet = carry; self.state = GS.BETTING
        return (result, carry, round(round_net, 2), is_bj)

# ─────────────────────────────────────────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────────────────────────────────────────
class Router:
    def __init__(self, root, session):
        self.root = root; self.session = session; self.current = None

    def navigate(self, name, **kwargs):
        if self.current:
            try: self.current.destroy()
            except: pass
            self.current = None
        if   name == "nickname":  self.current = NicknameScreen(self.root, self.session, self)
        elif name == "lobby":     self.current = LobbyScreen(self.root, self.session, self)
        elif name == "blackjack": self.current = BlackjackScreen(self.root, self.session, self)
        elif name == "gameover":  self.current = GameOverScreen(self.root, self.session, self)

# ─────────────────────────────────────────────────────────────────────────────
#  NICKNAME SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class NicknameScreen(tk.Frame):
    def __init__(self, root, session, router):
        super().__init__(root, bg=DARK)
        self.place(x=0, y=60, relwidth=1.0, relheight=1.0)
        self.session = session; self.router = router

        felt = make_felt()
        tw, th = felt.size
        cv = tk.Canvas(self, bg=DARK, highlightthickness=0)
        cv.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._fphs = []
        for y in range(0, 800, th):
            for x in range(0, 1280, tw):
                ph = ImageTk.PhotoImage(felt)
                cv.create_image(x, y, anchor="nw", image=ph)
                self._fphs.append(ph)

        for sym, x, y, sz in [("♠",180,180,90),("♥",1100,180,90),
                                ("♦",180,480,70),("♣",1100,480,70)]:
            cv.create_text(x, y, text=sym, font=("Georgia",sz,"bold"),
                           fill=GOLD, stipple="gray50")

        panel = tk.Frame(self, bg="#0d2b1a", bd=0)
        panel.place(relx=0.5, rely=0.46, anchor="center", width=480, height=360)

        tk.Label(panel, text="♠  Cmyrb Casino  ♠", font=("Georgia",22,"bold"),
                 bg="#0d2b1a", fg=GOLD).pack(pady=(28,4))
        tk.Label(panel, text="Enter your nickname to begin",
                 font=("Georgia",13), bg="#0d2b1a", fg="#aed6a0").pack(pady=(0,22))

        self._err = tk.StringVar()
        tk.Label(panel, textvariable=self._err, font=("Georgia",10),
                 bg="#0d2b1a", fg="#e74c3c").pack()

        entry_frame = tk.Frame(panel, bg=GOLD, padx=2, pady=2)
        entry_frame.pack(pady=4)
        self._nick_var = tk.StringVar()
        entry = tk.Entry(entry_frame, textvariable=self._nick_var,
                         font=("Georgia",16), width=18,
                         bg=DARK, fg="white", insertbackground=GOLD,
                         justify="center", relief="flat", bd=6)
        entry.pack()
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._submit())

        # ── CHANGE 1: fg="black" (was "white") ───────────────────────────────
        tk.Button(panel, text="▶  Play", font=("Georgia",15,"bold"),
                  bg="#27ae60", fg="black", activebackground="#1e8449",
                  relief="flat", padx=28, pady=10, cursor="hand2",
                  command=self._submit).pack(pady=20)

        nick = session.nickname
        if nick and LEADERBOARD.get(nick):
            rec = LEADERBOARD.get(nick)
            hint = "Welcome back, {}!  Peak: ${:.0f}".format(nick, rec["peak_balance"])
            tk.Label(panel, text=hint, font=("Georgia",10),
                     bg="#0d2b1a", fg=GOLD).pack()
            self._nick_var.set(nick)

    def _submit(self):
        nick = self._nick_var.get().strip()
        if not nick:
            self._err.set("Please enter a nickname."); return
        if len(nick) > 20:
            self._err.set("Max 20 characters."); return
        self.session.nickname = nick
        self.session.reset_session_stats()
        self.router.navigate("lobby")

# ─────────────────────────────────────────────────────────────────────────────
#  GAME OVER SCREEN
# ─────────────────────────────────────────────────────────────────────────────
class GameOverScreen(tk.Frame):
    def __init__(self, root, session, router):
        super().__init__(root, bg=DARK)
        self.place(x=0, y=60, relwidth=1.0, relheight=1.0)
        self.session = session; self.router = router

        felt = make_felt()
        tw, th = felt.size
        cv = tk.Canvas(self, bg=DARK, highlightthickness=0)
        cv.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._fphs = []
        for y in range(0, 800, th):
            for x in range(0, 1280, tw):
                ph = ImageTk.PhotoImage(felt)
                cv.create_image(x, y, anchor="nw", image=ph)
                self._fphs.append(ph)

        stats = session.session_stats_dict()
        nick  = session.nickname or "Player"

        lp = tk.Frame(self, bg=NAV, bd=2, relief="ridge")
        lp.place(x=60, y=30, width=480, height=600)

        tk.Label(lp, text="💀  Game Over", font=("Georgia",22,"bold"),
                 bg=NAV, fg="#e74c3c").pack(pady=(20,4))
        tk.Label(lp, text=nick, font=("Georgia",18,"bold"),
                 bg=NAV, fg=GOLD).pack(pady=(0,16))

        rows_s = [
            ("Rounds Played",   str(stats["rounds"])),
            ("Peak Balance",    "${:.2f}".format(stats["peak_balance"])),
            ("Biggest Win",     "${:.2f}".format(stats["biggest_win"])),
            ("Net This Session","${:.2f}".format(stats["net_total"])),
            ("Blackjacks Hit",  str(stats["blackjacks"])),
        ]
        for lbl, val in rows_s:
            row = tk.Frame(lp, bg=NAV); row.pack(fill="x", padx=24, pady=5)
            tk.Label(row, text=lbl, font=("Georgia",12), bg=NAV,
                     fg="#aed6a0", anchor="w").pack(side="left")
            tk.Label(row, text=val, font=("Georgia",12,"bold"), bg=NAV,
                     fg="white", anchor="e").pack(side="right")

        rec = LEADERBOARD.get(nick)
        if rec:
            tk.Label(lp, text="── All-Time Record ──", font=("Georgia",11),
                     bg=NAV, fg=GOLD).pack(pady=(18,4))
            rows_r = [
                ("Peak Balance",    "${:.2f}".format(rec["peak_balance"])),
                ("Biggest Win",     "${:.2f}".format(rec["biggest_win"])),
                ("Total Rounds",    str(rec["total_rounds"])),
                ("Total Net",       "${:.2f}".format(rec["total_won"])),
                ("Blackjacks",      str(rec["blackjacks"])),
                ("Sessions Played", str(rec["sessions"])),
            ]
            for lbl, val in rows_r:
                row = tk.Frame(lp, bg=NAV); row.pack(fill="x", padx=24, pady=3)
                tk.Label(row, text=lbl, font=("Georgia",11), bg=NAV,
                         fg="#aed6a0", anchor="w").pack(side="left")
                tk.Label(row, text=val, font=("Georgia",11,"bold"), bg=NAV,
                         fg="white", anchor="e").pack(side="right")

        btn_f = tk.Frame(lp, bg=NAV); btn_f.pack(pady=20)
        tk.Button(btn_f, text="▶  Play Again", font=("Georgia",13,"bold"),
                  bg="#27ae60", fg="black", activebackground="#1e8449",
                  relief="flat", padx=16, pady=8, cursor="hand2",
                  command=self._play_again).pack(side="left", padx=8)
        tk.Button(btn_f, text="👤  Change Player", font=("Georgia",11),
                  bg=NAV, fg=GOLD, activebackground=DARK,
                  relief="flat", padx=12, pady=8, cursor="hand2",
                  command=lambda: router.navigate("nickname")).pack(side="left", padx=8)

        rp = tk.Frame(self, bg=NAV, bd=2, relief="ridge")
        rp.place(x=580, y=30, width=640, height=600)

        tk.Label(rp, text="🏆  Leaderboard  —  Peak Balance",
                 font=("Georgia",16,"bold"), bg=NAV, fg=GOLD).pack(pady=(18,10))

        top = LEADERBOARD.top(10, key="peak_balance")
        headers = ["#","Player","Peak $","Best Win","Rounds","BJs"]
        col_w   = [30, 160, 100, 100, 70, 50]
        hrow = tk.Frame(rp, bg="#0a1f12"); hrow.pack(fill="x", padx=12)
        for h, w in zip(headers, col_w):
            tk.Label(hrow, text=h, font=("Georgia",11,"bold"), bg="#0a1f12",
                     fg=GOLD, width=w//9, anchor="w").pack(side="left")
        tk.Frame(rp, bg=GOLD, height=1).pack(fill="x", padx=12, pady=2)

        for rank_i, (pname, prec) in enumerate(top, 1):
            bg_c  = "#132b1c" if rank_i % 2 == 0 else NAV
            medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(rank_i, str(rank_i))
            is_me = (pname == nick)
            fg_c  = GOLD if is_me else "white"
            vals  = [medal, pname,
                     "${:.0f}".format(prec["peak_balance"]),
                     "${:.0f}".format(prec["biggest_win"]),
                     str(prec["total_rounds"]),
                     str(prec["blackjacks"])]
            drow = tk.Frame(rp, bg=bg_c); drow.pack(fill="x", padx=12, pady=1)
            for v, w in zip(vals, col_w):
                lbl = tk.Label(drow, text=v, font=("Georgia",11), bg=bg_c,
                               fg=fg_c, width=w//9, anchor="w")
                if is_me: lbl.config(font=("Georgia",11,"bold"))
                lbl.pack(side="left")

        if not top:
            tk.Label(rp, text="No records yet — you're the first!",
                     font=("Georgia",12), bg=NAV, fg="#aed6a0").pack(pady=30)

    def _play_again(self):
        self.session.reset_session_stats()
        self.router.navigate("lobby")

# ─────────────────────────────────────────────────────────────────────────────
#  LOBBY
# ─────────────────────────────────────────────────────────────────────────────
_GAMES = [
    {"name":"Blackjack","screen":"blackjack","active":True, "sym":"♠"},
    {"name":"Roulette", "screen":None,       "active":False,"sym":"◉"},
    {"name":"Slots",    "screen":None,       "active":False,"sym":"🎰"},
    {"name":"Poker",    "screen":None,       "active":False,"sym":"♣"},
    {"name":"Baccarat", "screen":None,       "active":False,"sym":"♦"},
    {"name":"Craps",    "screen":None,       "active":False,"sym":"⚄"},
]

def _rr_ph(w, h, r, fill, outline):
    img = Image.new("RGBA",(w,h),(0,0,0,0))
    ImageDraw.Draw(img).rounded_rectangle([0,0,w-1,h-1], radius=r,
                                          fill=fill, outline=outline, width=2)
    return ImageTk.PhotoImage(img)

class GameTile(tk.Canvas):
    def __init__(self, parent, game, router):
        super().__init__(parent, width=220, height=280, bg=DARK, highlightthickness=0)
        self._ph = []
        fill = "#1e5c36" if game["active"] else "#163d28"
        bg = _rr_ph(220,280,14,fill,GOLD); self._ph.append(bg)
        self.create_image(0,0,anchor="nw",image=bg)
        self.create_text(110,75,  text=game["sym"],  font=("Georgia",42,"bold"),
                         fill=GOLD if game["active"] else "#4a7a5a")
        self.create_text(110,148, text=game["name"], font=("Georgia",17,"bold"),
                         fill="#f5e6c8" if game["active"] else "#5a7a6a")
        if game["active"]:
            bp = _rr_ph(134,42,10,"#27ae60","#1e8449"); self._ph.append(bp)
            self.create_image(43,208,anchor="nw",image=bp)
            self.create_text(110,229,text="▶  Play",font=("Georgia",13,"bold"),fill="white")
            self.bind("<Button-1>", lambda e: router.navigate(game["screen"]))
            self.config(cursor="hand2")
        else:
            ov = ImageTk.PhotoImage(Image.new("RGBA",(220,280),(0,0,0,150)))
            self._ph.append(ov); self.create_image(0,0,anchor="nw",image=ov)
            bb = _rr_ph(148,38,8,GOLD,"#a07830"); self._ph.append(bb)
            self.create_image(36,212,anchor="nw",image=bb)
            self.create_text(110,231,text="Coming Soon",font=("Georgia",11,"bold"),fill="#1a1a1a")

class LobbyScreen(tk.Frame):
    def __init__(self, root, session, router):
        super().__init__(root, bg=DARK)
        self.place(x=0, y=60, relwidth=1.0, relheight=1.0)
        nick = session.nickname or "Player"
        tk.Label(self, text="Welcome, {}  —  Choose Your Game".format(nick),
                 font=("Georgia",20,"bold"), bg=DARK, fg=GOLD).pack(pady=(24,16))
        g = tk.Frame(self, bg=DARK); g.pack(expand=True)
        for i, game in enumerate(_GAMES):
            r,c = divmod(i,3)
            GameTile(g, game, router).grid(row=r, column=c, padx=16, pady=14)

# ─────────────────────────────────────────────────────────────────────────────
#  BLACKJACK SCREEN
# ─────────────────────────────────────────────────────────────────────────────
HAND_GAP = 24

class BlackjackScreen(tk.Frame):
    def __init__(self, root, session, router):
        super().__init__(root, bg=DARK)
        self.place(x=0, y=60, relwidth=1.0, relheight=1.0)
        self.root = root; self.session = session; self.router = router
        self._pending = 0.0; self._chip_stack = []
        self._card_ids = []; self._betc_ids = []
        self._overlay = None; self._felt = make_felt()
        self.game = BJGame(session)
        self._build_ui(); self._render_table(); self._update_buttons()

    def _build_ui(self):
        W, H = 1280, 740; self._W = W; self._H = H
        cv = tk.Canvas(self, width=W, height=H, bg=DARK, highlightthickness=0)
        cv.pack(fill="both", expand=True); self.cv = cv
        tw, th = self._felt.size; self._fphs = []
        for y in range(0, H, th):
            for x in range(0, W, tw):
                ph = ImageTk.PhotoImage(self._felt)
                cv.create_image(x, y, anchor="nw", image=ph); self._fphs.append(ph)
        cv.create_arc(80, H//2-60, W-80, H+300, start=0, extent=180,
                      outline=GOLD, width=3, style="arc")
        cv.create_text(W//2, 78,  text="DEALER", font=("Georgia",13,"bold"), fill=GOLD)
        cv.create_text(W//2, 390, text="PLAYER", font=("Georgia",13,"bold"), fill=GOLD)
        self._id_dscore = cv.create_text(W//2, 102, text="",
                                         font=("Georgia",14,"bold"), fill="white")
        self._id_pscore = cv.create_text(W//2, 414, text="",
                                         font=("Georgia",14,"bold"), fill="white")
        cx = W//2; self._bcx = cx; self._bcy = 530
        cv.create_oval(cx-60,475,cx+60,590, outline=GOLD, width=2, dash=(6,3))
        self._id_betlbl = cv.create_text(cx, 575, text="$0.00",
                                         font=("Georgia",12,"bold"), fill=GOLD)
        self._ppv = tk.StringVar(value="0"); self._t3v = tk.StringVar(value="0")
        self._make_sb(60,    474, "Perfect Pairs $", self._ppv)
        self._make_sb(W-205, 474, "21+3 $",          self._t3v)
        self._build_chip_row(cx, 630); self._build_buttons(cx, 694)
        self._id_bal = cv.create_text(W-130, 30,
                                      text="${:.2f}".format(self.session.balance),
                                      font=("Georgia",15,"bold"), fill=GOLD)
        self.session.add_listener(self._on_balance)
        tk.Button(self, text="◀  Lobby", font=("Georgia",11),
                  bg=NAV, fg=GOLD, activebackground=DARK, bd=0, cursor="hand2",
                  command=lambda: self.router.navigate("lobby")).place(x=10, y=8)
        nick = self.session.nickname or ""
        if nick:
            cv.create_text(14, 30, anchor="w", text=nick,
                           font=("Georgia",12,"bold"), fill=GOLD)

    def _on_balance(self, b):
        try: self.cv.itemconfig(self._id_bal, text="${:.2f}".format(b))
        except Exception: pass

    def _make_sb(self, x, y, lbl, var):
        f = tk.Frame(self, bg=NAV, bd=1, relief="ridge")
        tk.Label(f, text=lbl, font=("Georgia",9), bg=NAV, fg=GOLD).pack()
        tk.Entry(f, textvariable=var, width=6, font=("Georgia",11),
                 bg=DARK, fg="white", insertbackground="white", justify="center").pack()
        self.cv.create_window(x, y, window=f, anchor="nw")

    def _build_chip_row(self, cx, y):
        spacing = 76; sx = cx - (4*spacing)//2
        for i, d in enumerate(CHIP_DENOMS):
            x = sx + i*spacing
            cid = self.cv.create_image(x, y, anchor="center", image=CHIP_IMG[d])
            self.cv.tag_bind(cid, "<Button-1>", lambda e, a=d: self._chip_click(a))
            self.cv.tag_bind(cid, "<Enter>",    lambda e: self.cv.config(cursor="hand2"))
            self.cv.tag_bind(cid, "<Leave>",    lambda e: self.cv.config(cursor=""))

    def _build_buttons(self, cx, y):
        specs = [("Clear","#e74c3c",self._do_clear),("Deal","#27ae60",self._do_deal),
                 ("Hit","#2980b9",self._do_hit),("Stand","#c0392b",self._do_stand),
                 ("Dbl","#8e44ad",self._do_double),("Split","#e67e22",self._do_split)]
        self._btns = {}; spacing = 116; sx = cx-(len(specs)-1)*spacing//2
        for i, (lbl, col, cmd) in enumerate(specs):
            b = tk.Button(self, text=lbl, font=("Georgia",13,"bold"),
                          width=6, height=2, bg="white", fg="black",
                          activebackground=col, activeforeground="white",
                          relief="solid", bd=2, cursor="hand2", command=cmd)
            self.cv.create_window(sx+i*spacing, y, window=b); self._btns[lbl] = b

    def _chip_click(self, denom):
        if self.game.state != GS.BETTING: return
        if self._pending + denom > self.session.balance: return
        self._pending += denom
        for entry in self._chip_stack:
            if entry[0] == denom: entry[1] += 1; break
        else: self._chip_stack.append([denom, 1])
        self._render_bet_circle()

    def _render_bet_circle(self):
        for cid in self._betc_ids: self.cv.delete(cid)
        self._betc_ids.clear()
        self.cv.itemconfig(self._id_betlbl, text="${:.2f}".format(self._pending))
        if not self._pending: return
        display_stack = _amount_to_chip_stack(self._pending)
        flat = []
        for denom, count in sorted(display_stack, key=lambda x: -x[0]):
            flat.extend([denom] * min(count, 4))
        flat = flat[:8]; chip_h = 10; cx = self._bcx; cy = self._bcy-20
        base_y = cy + (len(flat)-1)*chip_h//2
        for idx, d in enumerate(flat):
            img = CHIP_IMG.get(d, CHIP_IMG[5])
            cid = self.cv.create_image(cx, base_y-idx*chip_h, anchor="center", image=img)
            self._betc_ids.append(cid)

    def _do_clear(self):
        if self.game.state != GS.BETTING: return
        self._pending = 0.0; self._chip_stack = []; self._render_bet_circle()

    def _do_deal(self):
        if self.game.state != GS.BETTING or self._pending <= 0: return
        try:    pp = max(0.0, float(self._ppv.get()))
        except: pp = 0.0
        try:    t3 = max(0.0, float(self._t3v.get()))
        except: t3 = 0.0
        self.game.bet = 0.0; self.game.sb_amounts = {}
        if not self.game.set_bet(self._pending): return
        if pp > 0: self.game.set_side_bet("pp", pp)
        if t3 > 0: self.game.set_side_bet("t3", t3)
        for cid in self._betc_ids: self.cv.delete(cid)
        self._betc_ids.clear(); self._pending = 0.0; self._chip_stack = []
        self.cv.itemconfig(self._id_betlbl, text="$0.00")
        if not self.game.deal(): return
        self._render_table(); self._update_buttons()
        if self.game.player_has_bj():
            self._update_buttons(all_off=True)
            self.after(800, self._safe(self._start_dealer))

    def _do_hit(self):
        if self.game.state != GS.PLAYER_TURN: return
        result = self.game.hit(); self._render_table()
        if result == PLAYER: self._update_buttons()
        elif result == DEALER:
            self._update_buttons(all_off=True)
            self.after(400, self._safe(self._start_dealer))

    def _do_stand(self):
        if self.game.state != GS.PLAYER_TURN: return
        result = self.game.stand(); self._render_table()
        if result == PLAYER: self._update_buttons()
        elif result == DEALER:
            self._update_buttons(all_off=True)
            self.after(400, self._safe(self._start_dealer))

    def _do_double(self):
        if self.game.state != GS.PLAYER_TURN: return
        result = self.game.double_down()
        if result == FAILED: return
        self._render_table()
        if result == PLAYER: self._update_buttons()
        elif result == DEALER:
            self._update_buttons(all_off=True)
            self.after(400, self._safe(self._start_dealer))

    def _do_split(self):
        if self.game.state != GS.PLAYER_TURN: return
        result = self.game.split()
        if result == FAILED: return
        self._render_table(); self._update_buttons()

    def _start_dealer(self):
        if self.game.state == GS.PLAYER_TURN: self.game.state = GS.DEALER_TURN
        self._render_table(); self._dealer_step()

    def _dealer_step(self):
        if self.game.dealer_needs_hit():
            self.game.dealer_hit(); self._render_table()
            self.after(550, self._safe(self._dealer_step))
        else:
            self.after(400, self._safe(self._finish_round))

    def _finish_round(self):
        msg, carry, round_net, is_bj = self.game.payout_and_reset()
        self.session.record_round(round_net, is_bj)
        self._render_table()
        if self.session.balance <= 0:
            LEADERBOARD.update(self.session.nickname or "Anonymous",
                               self.session.session_stats_dict())
            self._show_overlay("💀  BUST!  You're out of chips!")
            self.after(2200, self._safe(lambda: self.router.navigate("gameover")))
            return
        self._show_overlay(msg)
        self.after(2400, self._safe(lambda: self._begin_new_round(carry)))

    def _begin_new_round(self, carry):
        try:
            self._dismiss_overlay(); self._clear_cards()
            self._pending    = carry if carry > 0 else 0.0
            self._chip_stack = _amount_to_chip_stack(self._pending) if self._pending > 0 else []
            self._render_bet_circle()
            if self.game.reshuffle_flag:
                self.game.reshuffle_flag = False; self._show_reshuffle()
        finally:
            self._update_buttons()

    def _render_table(self):
        g = self.game; reveal = (g.state != GS.PLAYER_TURN and len(g.dealer_hand.cards)>0)
        if g.dealer_hand.cards:
            txt = ("Dealer: {}".format(g.dealer_hand.total()) if reveal
                   else "Dealer: {}".format(g.dealer_hand.cards[0].value))
            self.cv.itemconfig(self._id_dscore, text=txt)
        else: self.cv.itemconfig(self._id_dscore, text="")
        if g.player_hands and g.player_hands[0].cards:
            idx = min(g.hand_idx, len(g.player_hands)-1)
            self.cv.itemconfig(self._id_pscore,
                               text="Player: {}".format(g.player_hands[idx].total()))
        else: self.cv.itemconfig(self._id_pscore, text="")
        self._clear_cards(); W = self._W; gap = CW+10
        dc = g.dealer_hand.cards
        if dc:
            ds = W//2 - len(dc)*gap//2
            for i, card in enumerate(dc):
                key = card.key() if (i!=1 or reveal) else "back"
                img = CARD_IMG.get(key, CARD_IMG["back"])
                self._card_ids.append(self.cv.create_image(ds+i*gap, 116, anchor="nw", image=img))
        active_hands = [h for h in g.player_hands if h.cards]
        if active_hands:
            hand_widths = [len(h.cards)*gap for h in active_hands]
            total_w = sum(hand_widths) + HAND_GAP*(len(active_hands)-1)
            x_cursor = W//2 - total_w//2
            for hi, hand in enumerate(g.player_hands):
                if not hand.cards: continue
                hx = x_cursor
                for i, card in enumerate(hand.cards):
                    img = CARD_IMG.get(card.key(), CARD_IMG["back"])
                    iid = self.cv.create_image(hx+i*gap, 428, anchor="nw", image=img)
                    self._card_ids.append(iid)
                    if hi == g.hand_idx and g.state == GS.PLAYER_TURN:
                        # ── CHANGE 2: outline="#e74c3c" (was GOLD) ───────────
                        self._card_ids.append(self.cv.create_rectangle(
                            hx+i*gap-2, 426,
                            hx+i*gap+CW+2, 426+CH+2,
                            outline="#e74c3c", width=2))
                if len(g.player_hands)>1 and hi<len(g.player_hands)-1:
                    div_x = hx+len(hand.cards)*gap+HAND_GAP//2
                    self._card_ids.append(self.cv.create_line(
                        div_x,418,div_x,428+CH+10, fill=GOLD,width=1,dash=(4,3)))
                x_cursor += len(hand.cards)*gap + HAND_GAP

    def _clear_cards(self):
        for cid in self._card_ids: self.cv.delete(cid)
        self._card_ids.clear()

    def _update_buttons(self, all_off=False):
        g = self.game
        betting = (not all_off) and (g.state == GS.BETTING)
        playing = (not all_off) and (g.state == GS.PLAYER_TURN)
        h = (g.player_hands[g.hand_idx]
             if g.player_hands and g.hand_idx < len(g.player_hands) else None)
        can_dbl  = playing and h and h.can_dbl()   and g.bet <= g.session.balance
        can_splt = playing and h and h.can_split() and g.bet <= g.session.balance
        on = lambda flag: "normal" if flag else "disabled"
        self._btns["Clear"].config(state=on(betting)); self._btns["Deal"].config(state=on(betting))
        self._btns["Hit"].config(state=on(playing));   self._btns["Stand"].config(state=on(playing))
        self._btns["Dbl"].config(state=on(can_dbl));   self._btns["Split"].config(state=on(can_splt))

    def _show_overlay(self, msg):
        W, H = self._W, self._H; self._dismiss_overlay()
        r = self.cv.create_rectangle(W//2-270, H//2-75, W//2+270, H//2+75,
                                     fill="#000000", stipple="gray50", outline=GOLD, width=3)
        t = self.cv.create_text(W//2, H//2, text=msg,
                                font=("Georgia",22,"bold"), fill=GOLD, justify="center")
        self._overlay = (r, t)

    def _dismiss_overlay(self):
        if self._overlay:
            try: self.cv.delete(self._overlay[0]); self.cv.delete(self._overlay[1])
            except Exception: pass
            self._overlay = None

    def _show_reshuffle(self):
        W, H = self._W, self._H
        oid = self.cv.create_rectangle(W//2-215,H//2-58,W//2+215,H//2+58,
                                       fill=NAV, outline=GOLD, width=3)
        tid = self.cv.create_text(W//2, H//2, text="Shuffling new shoe...",
                                  font=("Georgia",18,"bold"), fill=GOLD)
        self.after(1500, lambda: (self.cv.delete(oid), self.cv.delete(tid)))

    def _safe(self, fn):
        def wrapper():
            try: fn()
            except Exception: traceback.print_exc()
        return wrapper

# ─────────────────────────────────────────────────────────────────────────────
#  APP SHELL
# ─────────────────────────────────────────────────────────────────────────────
class CasinoApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cmyrb Casino")
        self.root.geometry("1280x800")
        self.root.minsize(1024,700)
        self.root.configure(bg=DARK)
        build_caches()
        self.session = SessionState(balance=START_BAL)
        self._build_nav()
        self.router  = Router(self.root, self.session)
        self.router.navigate("nickname")

    def _build_nav(self):
        nav = tk.Canvas(self.root, height=60, bg=NAV, highlightthickness=0)
        nav.pack(side="top", fill="x")
        nav.create_text(22, 30, anchor="w", text="♠  Cmyrb Casino  ♠",
                        font=("Georgia",20,"bold"), fill=GOLD)
        self._bv = tk.StringVar(value="Balance:  ${:.2f}".format(START_BAL))
        tk.Label(nav, textvariable=self._bv, font=("Georgia",14,"bold"),
                 bg=NAV, fg=GOLD).place(relx=1.0, rely=0.5, anchor="e", x=-20)
        self.session.add_listener(lambda b: self._bv.set("Balance:  ${:.2f}".format(b)))

    def run(self): self.root.mainloop()

if __name__ == "__main__":
    CasinoApp().run()