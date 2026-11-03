# -*- coding: utf-8 -*-
"""上班鼓励器 - 实时计算你今天赚了多少钱"""
import json
import os
import calendar
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "上班鼓励器"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ShangBanGuLiQi")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# 统一配色（暖米纸底 + 墨黑 + 朱砂红，设置页与首页一致）
C_BG = "#F6F1E7"        # 背景暖米色
C_CARD = "#FBF8F1"      # 卡片
C_LINE = "#E5DCC9"      # 卡片描边
C_TEXT = "#2A231C"      # 墨黑
C_SUB = "#6B5B45"       # 咖褐
C_RED = "#C1432F"       # 朱砂红
C_BTN = "#2A231C"       # 深色按钮
C_BAR = "#4A7BB5"       # 进度条蓝
C_INPUT = "#FFFFFF"     # 输入框底
C_INPUT_LINE = "#D9CDB6"
C_SEL = "#EFE7D6"       # 未选中的浅块

FONT = "Microsoft YaHei UI"
WEEK_CN = ["一", "二", "三", "四", "五", "六", "日"]  # index 0=周一

# ============================================================
# 内置文案库：按「今日工时进度」节点触发
# 花括号里的占位符在运行时替换为实时数据（金额/百分比/剩余时间）
# ============================================================
MESSAGE_LIBRARY = [
    (0, ["刚开工，先把今天的早饭钱赚回来。",
         "计时开始，今天的第一块钱正在到账。"]),
    (10, ["进度 {pct}%，今天已赚 {earned}，一杯奶茶的钱到手了。",
          "{earned} 已入账，摸会儿鱼的功夫就够买瓶水。"]),
    (20, ["两成进度，{earned} 到账，中午的饭钱稳了。",
          "已经赚回一顿午饭：{earned}。"]),
    (30, ["三分之一走完，今天进账 {earned}。",
          "进度 {pct}%，{earned} 落袋，别急着摸鱼。"]),
    (40, ["四成进度，{earned} 到手，下午继续。",
          "{earned} 已赚，今天的钱拿到了快一半。"]),
    (50, ["过半了！今天已赚 {earned}，剩下的都是净赚。",
          "进度 {pct}%，{earned} 入账，{item}已经赚回来了。"]),
    (60, ["六成进度，{earned} 到手，{item}也有了。",
          "已赚 {earned}，离满勤 {full} 越来越近。"]),
    (70, ["七成进度，{earned} 进账，下午茶不用犹豫。",
          "{earned} 已到手，再撑一会儿就收工。"]),
    (80, ["八成进度，{earned} 到手，胜利在望。",
          "已赚 {earned}，还剩 {remain} 就下班。"]),
    (90, ["只剩 {remain}，今天 {earned} 基本落袋。",
          "最后冲刺，再赚 {left} 就是满勤 {full}。"]),
    (100, ["收工！今天 {earned} 全部到手，辛苦了。"]),
]

REST_MESSAGES = [
    "今天休息，养好精神明天继续赚。",
    "休息日也在悄悄变强，明天再战。",
    "今天不用打卡，时间全归你自己。",
]
BEFORE_MESSAGES = [
    "还没上班，先攒点精神。",
    "开工前的时间，属于你自己。",
]
PAUSED_MESSAGE = "计时器已关闭，钱袋暂时合上了。"

# 文案里提到的物品（只在已赚够时才会出现）
ITEM_LIST = [("一杯奶茶", 15), ("一顿快餐", 30), ("一张电影票", 45),
             ("一件T恤", 99), ("一双球鞋", 399), ("一部手机", 4999)]


def default_config():
    return {
        "title": "今日收入",
        "salary": 8000.0,
        "pay_days": 22,          # 计薪天数 天/月
        "payday": 15,            # 发薪日
        "bonus": 0.0,            # 全勤奖/月
        "start": "09:00",
        "end": "18:00",
        "lunch_min": 0,          # 午休扣除分钟，0=不扣
        "decimals": 4,           # 金额小数位
        "workdays": [0, 1, 2, 3, 4],  # 0=周一 ... 6=周日
    }


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return None
    d = default_config()
    if "rest_per_week" in cfg and "workdays" not in cfg:
        cfg["workdays"] = [0, 1, 2, 3, 4] if cfg["rest_per_week"] == 2 else [0, 1, 2, 3, 4, 5]
    for k, v in d.items():
        cfg.setdefault(k, v)
    return cfg


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def parse_hm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def month_workdays(year, month, workdays):
    days = calendar.monthrange(year, month)[1]
    return sum(1 for d in range(1, days + 1)
               if datetime.date(year, month, d).weekday() in workdays)


# ============================================================
# 时间选择器（点开选择 时 / 分）
# ============================================================
class TimePicker(tk.Toplevel):
    def __init__(self, master, init="09:00", on_pick=None):
        super().__init__(master)
        self.on_pick = on_pick
        self.result = None
        self.configure(bg=C_CARD)
        self.title("选择时间")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

        h_str, m_str = init.split(":")
        self.cur_h, self.cur_m = int(h_str), int(m_str)

        wrap = tk.Frame(self, bg=C_CARD)
        wrap.pack(padx=12, pady=10)

        LH, LW = 7, 4
        # 时
        col1 = tk.Frame(wrap, bg=C_CARD)
        col1.pack(side="left", padx=(0, 8))
        tk.Label(col1, text="时", bg=C_CARD, fg=C_SUB, font=(FONT, 9)).pack(pady=(0, 2))
        self.lb_h = self._make_list(col1, [f"{i:02d}" for i in range(24)], self.cur_h, LH, LW)

        tk.Label(wrap, text=":", bg=C_CARD, fg=C_TEXT, font=(FONT, 14, "bold")
                 ).pack(side="left", pady=(14, 0))

        # 分
        col2 = tk.Frame(wrap, bg=C_CARD)
        col2.pack(side="left", padx=(8, 0))
        tk.Label(col2, text="分", bg=C_CARD, fg=C_SUB, font=(FONT, 9)).pack(pady=(0, 2))
        self.lb_m = self._make_list(col2, [f"{i:02d}" for i in range(60)], self.cur_m, LH, LW)

        bar = tk.Frame(self, bg=C_CARD)
        bar.pack(fill="x", padx=12, pady=(0, 12))
        tk.Button(bar, text="取消", command=self.destroy, bg=C_SEL, fg=C_SUB,
                  relief="flat", cursor="hand2", font=(FONT, 10),
                  activebackground=C_LINE, activeforeground=C_TEXT
                  ).pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 5))
        tk.Button(bar, text="确定", command=self.confirm, bg=C_RED, fg="white",
                  relief="flat", cursor="hand2", font=(FONT, 10, "bold"),
                  activebackground="#A83A28", activeforeground="white"
                  ).pack(side="left", fill="x", expand=True, ipady=5)

        # 定位到锚点控件正下方水平居中
        self.update_idletasks()
        x = master.winfo_rootx() + master.winfo_width() // 2 - self.winfo_width() // 2
        y = master.winfo_rooty() + master.winfo_height() + 4
        x = max(10, min(x, self.winfo_screenwidth() - self.winfo_width() - 10))
        y = max(10, min(y, self.winfo_screenheight() - self.winfo_height() - 40))
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.lb_h.focus_set()
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.confirm())

    def _make_list(self, parent, items, idx, height, width):
        holder = tk.Frame(parent, bg=C_INPUT, highlightthickness=1,
                          highlightbackground=C_INPUT_LINE)
        holder.pack()
        lb = tk.Listbox(holder, height=height, width=width, font=(FONT, 11),
                        bg=C_INPUT, fg=C_TEXT, relief="flat", bd=0,
                        highlightthickness=0, exportselection=False,
                        activestyle="none", selectbackground=C_TEXT,
                        selectforeground="white", justify="center")
        sb = tk.Scrollbar(holder, orient="vertical", command=lb.yview, width=8)
        lb.config(yscrollcommand=sb.set)
        lb.pack(side="left", padx=(2, 0), pady=2)
        sb.pack(side="left", fill="y")
        for it in items:
            lb.insert("end", it)
        lb.selection_set(idx)
        lb.see(max(0, idx - 2))
        lb.bind("<ButtonRelease-1>", lambda e: None)
        return lb

    def confirm(self):
        sel_h = self.lb_h.curselection()
        sel_m = self.lb_m.curselection()
        h = int(self.lb_h.get(sel_h[0])) if sel_h else self.cur_h
        m = int(self.lb_m.get(sel_m[0])) if sel_m else self.cur_m
        self.result = f"{h:02d}:{m:02d}"
        if self.on_pick:
            self.on_pick(self.result)
        self.destroy()


# ============================================================
# 设置窗口（与首页同配色；Toplevel 子窗口，保存不会退出程序）
# ============================================================
class SettingsWindow(tk.Toplevel):
    def __init__(self, master, cfg=None, first_run=False):
        super().__init__(master)
        self.cfg_in = cfg or default_config()
        self.first_run = first_run
        self.result = None
        self.title("上班鼓励器 - 初始设置" if first_run else "上班鼓励器 - 设置")
        self.configure(bg=C_BG)
        w, h = 420, 812
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(10, (sh - h) // 2 - 28)}")
        self.resizable(False, False)
        if first_run:
            self.protocol("WM_DELETE_WINDOW", self.on_close_request)
        self.build_ui()
        self.grab_set()
        self.focus_set()

    # ---------- 控件小工具 ----------
    def section(self, text):
        tk.Label(self, text=text, bg=C_BG, fg=C_SUB,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=24, pady=(14, 6))

    def card(self):
        f = tk.Frame(self, bg=C_CARD, highlightthickness=1,
                     highlightbackground=C_LINE)
        f.pack(fill="x", padx=20, ipady=4)
        return f

    def entry_row(self, parent, label, value, unit="", width=12):
        tk.Label(parent, text=label, bg=C_CARD, fg=C_TEXT,
                 font=(FONT, 10)).pack(side="left", padx=(14, 10))
        if isinstance(value, float) and value == int(value):
            value = int(value)
        e = tk.Entry(parent, font=(FONT, 11), bg=C_INPUT, fg=C_TEXT,
                     relief="flat", insertbackground=C_TEXT, justify="center",
                     width=width, highlightthickness=1,
                     highlightbackground=C_INPUT_LINE, highlightcolor=C_RED)
        e.pack(side="left", ipady=5)
        e.insert(0, str(value))
        if unit:
            tk.Label(parent, text=unit, bg=C_CARD, fg=C_SUB,
                     font=(FONT, 10)).pack(side="left", padx=(8, 0))
        return e

    def time_row(self, parent, label, value):
        """时间选择器：点击弹出 时/分 选择面板"""
        tk.Label(parent, text=label, bg=C_CARD, fg=C_TEXT,
                 font=(FONT, 10)).pack(side="left", padx=(14, 10))
        btn = tk.Button(parent, text=value, font=(FONT, 11), bg=C_INPUT, fg=C_TEXT,
                        relief="flat", cursor="hand2", width=8, bd=0,
                        highlightthickness=1, highlightbackground=C_INPUT_LINE,
                        activebackground=C_SEL, activeforeground=C_TEXT)
        btn.pack(side="left", ipady=4)
        btn.config(command=lambda b=btn: self.pick_time(b))
        return btn

    def pick_time(self, btn):
        def apply(v):
            btn.config(text=v)
        # 以按钮自身为锚点，选择器弹在按钮正下方
        TimePicker(btn, btn.cget("text"), apply)

    def combo_row(self, parent, label, values, index):
        tk.Label(parent, text=label, bg=C_CARD, fg=C_TEXT,
                 font=(FONT, 10)).pack(side="left", padx=(14, 10))
        cmb = ttk.Combobox(parent, state="readonly", width=12, font=(FONT, 10),
                           values=values)
        cmb.current(index)
        cmb.pack(side="left", ipady=3)
        return cmb

    # ---------- 界面 ----------
    def build_ui(self):
        head = tk.Frame(self, bg=C_BG)
        head.pack(fill="x", padx=24, pady=(18, 2))
        tk.Label(head, text="◉", bg=C_BG, fg=C_RED, font=(FONT, 13, "bold")).pack(side="left")
        tk.Label(head, text="  收入计时器 · 设置", bg=C_BG, fg=C_TEXT,
                 font=(FONT, 15, "bold")).pack(side="left")
        tk.Label(self, text="改完点最下面的「保存设置」立即生效",
                 bg=C_BG, fg=C_SUB, font=(FONT, 9)).pack(anchor="w", padx=24, pady=(0, 2))

        # ===== 收入 =====
        self.section("收入")
        c1 = self.card()
        r1 = tk.Frame(c1, bg=C_CARD); r1.pack(fill="x", pady=6)
        self.e_title = self.entry_row(r1, "标题", self.cfg_in["title"], width=14)
        r2 = tk.Frame(c1, bg=C_CARD); r2.pack(fill="x", pady=6)
        self.e_salary = self.entry_row(r2, "月薪", self.cfg_in["salary"], "元")
        r3 = tk.Frame(c1, bg=C_CARD); r3.pack(fill="x", pady=6)
        self.e_paydays = self.entry_row(r3, "计薪天数", self.cfg_in["pay_days"], "天/月")
        r4 = tk.Frame(c1, bg=C_CARD); r4.pack(fill="x", pady=6)
        self.e_payday = self.entry_row(r4, "发薪日", self.cfg_in["payday"], "号")
        r5 = tk.Frame(c1, bg=C_CARD); r5.pack(fill="x", pady=6)
        self.e_bonus = self.entry_row(r5, "全勤奖", self.cfg_in["bonus"], "元/月")

        # ===== 时间 =====
        self.section("时间")
        c2 = self.card()
        r6 = tk.Frame(c2, bg=C_CARD); r6.pack(fill="x", pady=6)
        self.btn_start = self.time_row(r6, "上班", self.cfg_in["start"])
        tk.Label(r6, text="下班", bg=C_CARD, fg=C_TEXT,
                 font=(FONT, 10)).pack(side="left", padx=(16, 10))
        self.btn_end = self.time_row(r6, "", self.cfg_in["end"])
        r7 = tk.Frame(c2, bg=C_CARD); r7.pack(fill="x", pady=6)
        self.cmb_lunch = self.combo_row(r7, "午休扣除", ["不扣午休", "扣 30 分钟", "扣 1 小时"],
                                        {0: 0, 30: 1, 60: 2}.get(int(self.cfg_in.get("lunch_min", 0)), 0))

        # ===== 显示 =====
        self.section("显示")
        c3 = self.card()
        r8 = tk.Frame(c3, bg=C_CARD); r8.pack(fill="x", pady=6)
        self.cmb_dec = self.combo_row(r8, "金额小数位", ["0 位小数", "2 位小数", "4 位小数"],
                                      {0: 0, 2: 1, 4: 2}.get(int(self.cfg_in.get("decimals", 4)), 2))

        r9 = tk.Frame(c3, bg=C_CARD); r9.pack(fill="x", pady=8)
        tk.Label(r9, text="工作日", bg=C_CARD, fg=C_TEXT,
                 font=(FONT, 10)).pack(side="left", padx=(14, 10))
        self.wd_btns = []
        self.wd_selected = set(self.cfg_in["workdays"])
        for i, name in enumerate(WEEK_CN):
            b = tk.Button(r9, text=name, font=(FONT, 10, "bold"), relief="flat",
                          cursor="hand2", width=2, bd=0,
                          command=lambda i=i: self.toggle_wd(i))
            b.pack(side="left", padx=3, ipadx=2, ipady=4)
            self.wd_btns.append(b)
            self.refresh_wd_btn(i)

        # ===== 保存 =====
        tk.Button(self, text="保 存 设 置", command=self.on_save,
                  bg=C_RED, fg="white", activebackground="#A83A28",
                  activeforeground="white", relief="flat", cursor="hand2",
                  font=(FONT, 13, "bold")).pack(fill="x", padx=20, ipady=11, pady=(22, 20))

    def toggle_wd(self, i):
        if i in self.wd_selected:
            self.wd_selected.discard(i)
        else:
            self.wd_selected.add(i)
        self.refresh_wd_btn(i)

    def refresh_wd_btn(self, i):
        b = self.wd_btns[i]
        if i in self.wd_selected:
            b.config(bg=C_TEXT, fg="#FBF5E9", activebackground=C_TEXT,
                     activeforeground="#FBF5E9")
        else:
            b.config(bg=C_SEL, fg=C_SUB, activebackground=C_LINE,
                     activeforeground=C_TEXT)

    # ---------- 保存 ----------
    def on_save(self):
        try:
            title = self.e_title.get().strip() or "今日收入"
            salary = float(self.e_salary.get().strip())
            pay_days = int(float(self.e_paydays.get().strip()))
            payday = int(float(self.e_payday.get().strip()))
            bonus = float(self.e_bonus.get().strip() or "0")
            s, e = self.btn_start.cget("text"), self.btn_end.cget("text")
            sh, sm = s.split(":"); eh, em = e.split(":")
            assert 0 <= int(sh) < 24 and 0 <= int(sm) < 60
            assert 0 <= int(eh) < 24 and 0 <= int(em) < 60
            assert salary > 0 and 1 <= pay_days <= 31 and 1 <= payday <= 31
            lunch = {0: 0, 1: 30, 2: 60}[self.cmb_lunch.current()]
            decimals = {0: 0, 1: 2, 2: 4}[self.cmb_dec.current()]
            assert parse_hm(e) - parse_hm(s) > lunch, "下班时间必须晚于上班时间，且要留出午休时间"
        except AssertionError as ex:
            messagebox.showwarning("输入有误", str(ex) if str(ex) else "请检查填写内容", parent=self)
            return
        except Exception:
            messagebox.showwarning("输入有误", "请检查数字与时间格式是否正确", parent=self)
            return
        if not self.wd_selected:
            messagebox.showwarning("输入有误", "至少要选择一个工作日", parent=self)
            return
        self.result = {
            "title": title,
            "salary": salary,
            "pay_days": pay_days,
            "payday": payday,
            "bonus": bonus,
            "start": s,
            "end": e,
            "lunch_min": lunch,
            "decimals": decimals,
            "workdays": sorted(self.wd_selected),
        }
        save_config(self.result)
        self.grab_release()
        self.destroy()

    def on_close_request(self):
        if messagebox.askokcancel("还没设置完", "必须先完成设置才能使用，确定放弃并退出吗？", parent=self):
            self.grab_release()
            self.destroy()
            self.master.destroy()


# ============================================================
# 主界面
# ============================================================
class MainApp(tk.Tk):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.paused = False
        self.paused_earned = 0.0
        self.title(APP_NAME)
        self.configure(bg=C_BG)
        w, h = 420, 736
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(10, (sh - h) // 2 - 20)}")
        self.resizable(False, False)
        self.build_ui()
        self.tick()

    # ---------- 界面 ----------
    def build_ui(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", padx=18, pady=(14, 4))
        tk.Label(top, text="◉", bg=C_BG, fg=C_RED, font=(FONT, 13, "bold")).pack(side="left")
        tk.Label(top, text=" " + APP_NAME, bg=C_BG, fg=C_TEXT,
                 font=(FONT, 11, "bold")).pack(side="left")
        btn_set = tk.Label(top, text="⚙ 设置", bg=C_BG, fg=C_SUB, font=(FONT, 10), cursor="hand2")
        btn_set.pack(side="right")
        btn_set.bind("<Button-1>", lambda e: self.open_settings())

        self.lbl_now = tk.Label(self, text="", bg=C_BG, fg=C_TEXT, font=(FONT, 13, "bold"))
        self.lbl_now.pack(anchor="w", padx=20, pady=(6, 12))

        self.lbl_status = tk.Label(self, text="", bg=C_BG, fg=C_TEXT, font=(FONT, 26, "bold"))
        self.lbl_status.pack(anchor="w", padx=20)
        self.lbl_countdown = tk.Label(self, text="", bg=C_BG, fg=C_TEXT, font=(FONT, 13))
        self.lbl_countdown.pack(anchor="w", padx=20, pady=(4, 10))

        # 今日已赚卡片（标题可在设置里改）
        card1 = tk.Frame(self, bg=C_CARD, highlightthickness=1,
                         highlightbackground=C_LINE)
        card1.pack(fill="x", padx=18, pady=4, ipady=10)
        self.lbl_card_title = tk.Label(card1, text="", bg=C_CARD, fg=C_SUB, font=(FONT, 11))
        self.lbl_card_title.pack(anchor="w", padx=16)
        self.lbl_earned = tk.Label(card1, text="", bg=C_CARD, fg=C_TEXT,
                                   font=("Consolas", 30, "bold"))
        self.lbl_earned.pack(anchor="w", padx=16)
        self.lbl_rate = tk.Label(card1, text="", bg=C_CARD, fg=C_SUB, font=(FONT, 10))
        self.lbl_rate.pack(anchor="w", padx=16, pady=(2, 0))
        self.lbl_goal = tk.Label(card1, text="", bg=C_CARD, fg=C_SUB, font=(FONT, 10),
                                 wraplength=330, justify="left", anchor="w")
        self.lbl_goal.pack(anchor="w", fill="x", padx=16, pady=(3, 0))

        self.btn_toggle = tk.Button(self, text="关闭计时器", command=self.toggle_pause,
                                    bg=C_BTN, fg="white", activebackground="#4A4038",
                                    activeforeground="white", relief="flat", cursor="hand2",
                                    font=(FONT, 12, "bold"))
        self.btn_toggle.pack(fill="x", padx=18, pady=(10, 4), ipady=8)

        # 今日工时进度
        card2 = tk.Frame(self, bg=C_CARD, highlightthickness=1,
                         highlightbackground=C_LINE)
        card2.pack(fill="x", padx=18, pady=(10, 4), ipady=10)
        tk.Label(card2, text="今日工时进度", bg=C_CARD, fg=C_TEXT,
                 font=(FONT, 11, "bold")).pack(anchor="w", padx=16)
        self.bar = tk.Canvas(card2, bg=C_CARD, height=10, highlightthickness=0)
        self.bar.pack(fill="x", padx=16, pady=(6, 2))
        self.lbl_worktime = tk.Label(card2, text="", bg=C_CARD, fg=C_SUB, font=(FONT, 10))
        self.lbl_worktime.pack(anchor="w", padx=16)

        # 本月累计
        card3 = tk.Frame(self, bg=C_CARD, highlightthickness=1,
                         highlightbackground=C_LINE)
        card3.pack(fill="x", padx=18, pady=(10, 16), ipady=12)
        hdr = tk.Frame(card3, bg=C_CARD)
        hdr.pack(fill="x", padx=16)
        tk.Label(hdr, text="本月累计", bg=C_CARD, fg=C_TEXT,
                 font=(FONT, 11, "bold")).pack(side="left", pady=(2, 0))
        # 金额放在标题下一行，避免长数字被右侧挤掉
        self.lbl_month = tk.Label(card3, text="", bg=C_CARD, fg=C_TEXT,
                                  font=("Consolas", 22, "bold"), anchor="w")
        self.lbl_month.pack(anchor="w", fill="x", padx=16)
        row2 = tk.Frame(card3, bg=C_CARD)
        row2.pack(fill="x", padx=16, pady=(2, 0))
        tk.Label(row2, text="时薪", bg=C_CARD, fg=C_SUB, font=(FONT, 10)).pack(side="left")
        self.lbl_hour = tk.Label(row2, text="", bg=C_CARD, fg=C_SUB, font=(FONT, 10, "bold"))
        self.lbl_hour.pack(side="left", padx=(6, 0))
        self.lbl_full = tk.Label(row2, text="", bg=C_CARD, fg=C_SUB, font=(FONT, 10))
        self.lbl_full.pack(side="right")
        self.lbl_month_note = tk.Label(card3, text="", bg=C_CARD, fg=C_SUB, font=(FONT, 9),
                                       wraplength=340, justify="left")
        self.lbl_month_note.pack(anchor="w", padx=16, pady=(4, 0))

    # ---------- 计算 ----------
    def derived(self):
        cfg = self.cfg
        now = datetime.datetime.now()
        today = now.date()
        s_min = parse_hm(cfg["start"])
        e_min = parse_hm(cfg["end"])
        lunch = cfg.get("lunch_min", 0)
        paid_mins = (e_min - s_min) - lunch
        daily = (cfg["salary"] + cfg.get("bonus", 0)) / max(cfg["pay_days"], 1)
        rate_sec = daily / max(paid_mins * 60, 1)
        rate_hour = daily / max(paid_mins / 60, 0.1)
        return now, today, s_min, e_min, lunch, paid_mins, daily, rate_sec, rate_hour

    def is_workday(self, today):
        return today.weekday() in self.cfg["workdays"]

    def paid_minutes_so_far(self, cur, s_min, e_min, lunch):
        """已计薪分钟：扣除 12:00 起的午休与工作时段的重叠部分"""
        worked = max(0.0, min(cur, e_min) - s_min)
        if lunch <= 0:
            return worked
        l_start, l_end = 720, 720 + lunch
        overlap = max(0.0, min(cur, l_end) - max(s_min, l_start))
        return max(0.0, worked - overlap)

    def earned_today(self):
        now, today, s_min, e_min, lunch, paid_mins, _, rate_sec, _ = self.derived()
        if not self.is_workday(today):
            return 0.0
        cur = now.hour * 60 + now.minute + now.second / 60.0
        if cur <= s_min:
            return 0.0
        return self.paid_minutes_so_far(cur, s_min, e_min, lunch) * 60 * rate_sec

    def fmt_money(self, v):
        return f"¥{v:.{self.cfg['decimals']}f}"

    def build_message(self, workday, cur, s_min, e_min, pct, earned, daily, today):
        """从内置文案库按节点取词；占位符替换成实时数字"""
        if self.paused:
            return PAUSED_MESSAGE
        if not workday:
            return REST_MESSAGES[today.toordinal() % len(REST_MESSAGES)]
        if cur < s_min:
            return BEFORE_MESSAGES[today.toordinal() % len(BEFORE_MESSAGES)]
        if cur >= e_min:
            return f"已下班，今天 ¥{earned:.2f} 全部到手，辛苦了。"

        # 命中进度节点（0/10/20…/100）
        node = 0
        for th, _ in MESSAGE_LIBRARY:
            if pct >= th:
                node = th
        templates = dict(MESSAGE_LIBRARY)[node]

        # 只有真的赚够了，文案里才提物品名
        bought = None
        for name, price in ITEM_LIST:
            if earned >= price:
                bought = name
        cand = [t for t in templates if "{item}" not in t] if bought is None else templates
        cand = cand or templates

        tpl = cand[today.toordinal() % len(cand)]
        # 文案里的金额统一保留 2 位，读起来更顺（大数字仍按设置的小数位）
        return tpl.format(
            earned=f"¥{earned:.2f}",
            pct=f"{pct:.0f}",
            remain=self.fmt_cn(max(0.0, (e_min - cur) * 60)),
            left=f"¥{max(0.0, daily - earned):.2f}",
            full=f"¥{daily:.2f}",
            item=bought or "",
        )

    def tick(self):
        cfg = self.cfg
        now, today, s_min, e_min, lunch, paid_mins, daily, rate_sec, rate_hour = self.derived()
        wd_cn = "一二三四五六日"[now.weekday()]
        self.lbl_now.config(text=f"{today:%Y-%m-%d} 周{wd_cn}  {now:%H:%M:%S}")
        self.lbl_card_title.config(text=cfg["title"])

        workday = self.is_workday(today)
        cur = now.hour * 60 + now.minute + now.second / 60.0
        earned = self.paused_earned if self.paused else self.earned_today()

        if not workday:
            self.lbl_status.config(text="今天休息", fg=C_SUB)
            self.lbl_countdown.config(text="休息日也在悄悄变强，明天再战 💪")
            worked_min, pct = 0.0, 0.0
        elif cur < s_min:
            self.lbl_status.config(text="未上班", fg=C_SUB)
            self.lbl_countdown.config(text=f"距上班还有 {self.fmt_cn((s_min - cur) * 60)}，攒攒精神")
            worked_min, pct = 0.0, 0.0
        elif cur >= e_min:
            self.lbl_status.config(text="已下班", fg=C_RED)
            self.lbl_countdown.config(text="今天的钱已经落袋，安心休息 ✨")
            worked_min, pct = float(paid_mins), 100.0
        else:
            self.lbl_status.config(text="上班中", fg=C_TEXT)
            self.lbl_countdown.config(text=f"距下班还有 {self.fmt_cn((e_min - cur) * 60)}")
            worked_min = (self.paused_earned / rate_sec / 60) if (self.paused and rate_sec > 0) \
                else self.paid_minutes_so_far(cur, s_min, e_min, lunch)
            pct = min(100.0, worked_min / max(paid_mins, 1) * 100)

        self.lbl_earned.config(text=self.fmt_money(earned))
        self.lbl_rate.config(text=f"当前赚钱速度 ¥{rate_sec:.4f} / 秒")

        # 文案库：按今日进度节点取词，数字全部实时替换
        self.lbl_goal.config(text=self.build_message(
            workday, cur, s_min, e_min, pct, earned, daily, today))

        # 工时进度条
        if workday:
            self.bar.delete("all")
            wpx = max(self.bar.winfo_width(), 10) - 4
            self.bar.create_rectangle(2, 1, 2 + wpx, 9, fill="#EAE2D0", outline="")
            self.bar.create_rectangle(2, 1, 2 + wpx * pct / 100, 9, fill=C_BAR, outline="")
            self.lbl_worktime.config(text=f"已工作 {worked_min/60:.2f} / {paid_mins/60:.2f} 小时（{pct:.1f}%）")
        else:
            self.bar.delete("all")
            self.lbl_worktime.config(text="非工作日，进度条也要休息")

        # 本月累计 = 今天之前的工作日按满勤 + 今日已赚
        past_days = sum(1 for d in range(1, today.day) if self.is_workday(today.replace(day=d)))
        month_total = past_days * daily + earned
        self.lbl_month.config(text=self.fmt_money(month_total))
        self.lbl_hour.config(text=f"¥{rate_hour:.2f} /小时")
        self.lbl_full.config(text=f"今日满勤 ¥{daily:.2f}")
        self.lbl_month_note.config(
            text=f"已过的工作日按满勤计算（计薪 {cfg['pay_days']} 天/月，{cfg['payday']} 号发薪）"
                 f"，本月只算已赚，不含亏损。")

        self.after(1000, self.tick)

    @staticmethod
    def fmt_cn(sec):
        if sec <= 0:
            return "0秒"
        h = int(sec // 3600)
        m = int(sec % 3600 // 60)
        s = int(sec % 60)
        parts = []
        if h:
            parts.append(f"{h}小时")
        if m:
            parts.append(f"{m}分")
        if not h and s:
            parts.append(f"{s}秒")
        return "".join(parts)

    def toggle_pause(self):
        if not self.paused:
            self.paused_earned = self.earned_today()
            self.paused = True
            self.btn_toggle.config(text="开启计时器")
        else:
            self.paused = False
            self.btn_toggle.config(text="关闭计时器")

    def open_settings(self):
        dlg = SettingsWindow(self, self.cfg, first_run=False)
        self.wait_window(dlg)
        if dlg.result:
            self.cfg = dlg.result
            self.paused = False
            self.paused_earned = 0.0


def main():
    cfg = load_config()
    if cfg:
        MainApp(cfg).mainloop()
        return
    hidden = tk.Tk()
    hidden.withdraw()
    dlg = SettingsWindow(hidden, None, first_run=True)
    hidden.wait_window(dlg)
    if dlg.result:
        hidden.destroy()
        MainApp(dlg.result).mainloop()
    else:
        hidden.destroy()


if __name__ == "__main__":
    main()
