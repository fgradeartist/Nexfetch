"""
NexFetch v2.9
P1: No CMD popup on create account, no location field
P2: Downloader: images+videos merged, clip download (start-end, ratio)
P3: Music: no album art, lyrics from internet by song name, original title
P4: Scraper: Facebook + Instagram multi-method fallback
P5: Ecommerce: robust price/sale/description scraping
P6: Account in header: avatar + username next to notifications
P7: Switch user: Toplevel overlay, no blank screen
P8: Saved logins: hover/autocomplete dropdown on login
P9: Global mousewheel scroll + right-click paste everywhere
"""
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, scrolledtext
try:
    from core.server import start_server as _start_web_server
except Exception:
    _start_web_server = None
import threading, os, sys, subprocess, json, re, time, datetime
import shutil, hashlib, csv, random, string
import urllib.request, urllib.parse, urllib.error
from pathlib import Path

if getattr(sys,"frozen",False): APP_DIR=Path(sys.executable).parent
else: APP_DIR=Path(__file__).parent.parent

CONFIG_FILE=APP_DIR/"config.json"; USERS_FILE=APP_DIR/"users.json"
SAVED_LOGINS_FILE=APP_DIR/"saved_logins.json"
FLAGS=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0

T={
    "bg":"#080c14","bg2":"#0d1117","bg3":"#111827","bg4":"#1a2332","card":"#0f1724",
    "acc":"#b3100f","acc2":"#ff2020","acc3":"#8b0000",
    "text":"#f0f4f8","muted":"#64748b","red":"#ef4444","green":"#22c55e",
    "yellow":"#f59e0b","cyan":"#06b6d4","log_fg":"#fca5a5","log_bg":"#050810","border":"#1e2d3d",
}
DEFAULT_CFG={**T,
    "tool_name":"NexFetch","author":"fgradeartist","version":"2.9","license":"MIT",
    "font_size":9,"font_family":"Consolas","logo_path":"","bg_image":"",
    "dl_path":str(Path.home()/"Downloads"/"NexFetch"),
    "admin_mode":False,"admin_username":"","invite_codes":["NEXFETCH2024"],
}

def hpw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def load_cfg():
    if CONFIG_FILE.exists():
        try: return {**DEFAULT_CFG,**json.loads(CONFIG_FILE.read_text("utf-8"))}
        except: pass
    return dict(DEFAULT_CFG)
def save_cfg(c): CONFIG_FILE.write_text(json.dumps(c,indent=2),"utf-8")
def load_users():
    if USERS_FILE.exists():
        try: return json.loads(USERS_FILE.read_text("utf-8"))
        except: pass
    return {}
def save_users(u): USERS_FILE.write_text(json.dumps(u,indent=2),"utf-8")
def load_saved_logins():
    if SAVED_LOGINS_FILE.exists():
        try: return json.loads(SAVED_LOGINS_FILE.read_text("utf-8"))
        except: pass
    return []
def save_saved_logins(lst): SAVED_LOGINS_FILE.write_text(json.dumps(lst[:10],indent=2),"utf-8")
def udir(u):
    d=APP_DIR/"userdata"/u; d.mkdir(parents=True,exist_ok=True); return d


# ── Loading overlay ─────────────────────────────────────
class LoadingOverlay:
    def __init__(self,parent,msg="Working..."):
        self._parent=parent; self._alive=True
        self.overlay=tk.Frame(parent,bg="#080c14")
        self.overlay.place(x=0,y=0,relwidth=1,relheight=1); self.overlay.lift()
        box=tk.Frame(self.overlay,bg=T["bg2"],highlightthickness=2,highlightbackground=T["acc"])
        box.place(relx=0.5,rely=0.5,anchor="center")
        self._spin=tk.StringVar(value="◐")
        tk.Label(box,textvariable=self._spin,font=("Segoe UI",32),fg=T["acc"],bg=T["bg2"]).pack(pady=(20,4),padx=50)
        self._msg=tk.StringVar(value=msg)
        tk.Label(box,textvariable=self._msg,font=("Segoe UI",11,"bold"),fg=T["text"],bg=T["bg2"]).pack(pady=(0,20))
        self._f=["◐","◓","◑","◒"]; self._i=0; self._tick()
    def _tick(self):
        if self._alive: self._spin.set(self._f[self._i%4]); self._i+=1; self._parent.after(110,self._tick)
    def update(self,msg): self._msg.set(msg)
    def destroy(self):
        self._alive=False
        try: self.overlay.destroy()
        except: pass


# ── Notifications ────────────────────────────────────────
class NotifCenter:
    def __init__(self,root):
        self.root=root; self._toasts=[]; self._history=[]; self._panel=None
    def push(self,title,msg="",kind="info",ms=4000):
        self._history.insert(0,{"time":datetime.datetime.now().strftime("%H:%M"),
                                 "title":str(title)[:60],"msg":str(msg)[:80],"kind":kind})
        self._history=self._history[:40]
        self._toast(str(title),str(msg),kind,ms)
        if self._panel and self._panel.winfo_exists(): self._rebuild_panel()
    def _toast(self,title,msg,kind,ms):
        cols={"info":T["cyan"],"warn":T["yellow"],"error":T["acc"],"ok":T["green"]}
        acc=cols.get(kind,T["cyan"])
        top=tk.Toplevel(self.root); top.overrideredirect(True); top.attributes("-topmost",True); top.configure(bg=acc)
        inner=tk.Frame(top,bg=T["bg2"],padx=14,pady=10); inner.pack(padx=1,pady=1)
        icons={"info":"◈","warn":"▲","error":"✕","ok":"✔"}
        row=tk.Frame(inner,bg=T["bg2"]); row.pack(fill="x")
        tk.Label(row,text=f"{icons.get(kind,'◈')} {title}",font=("Segoe UI",10,"bold"),fg=acc,bg=T["bg2"]).pack(side="left")
        tk.Label(row,text="✕",font=("Segoe UI",9),fg=acc,bg=T["bg2"],cursor="hand2").pack(side="right")
        row.winfo_children()[-1].bind("<Button-1>",lambda e:self._dismiss(top))
        if msg: tk.Label(inner,text=str(msg)[:55],font=("Segoe UI",9),fg="#aaa",bg=T["bg2"],wraplength=260).pack(anchor="w",pady=(3,0))
        self._toasts.append(top); self._restack()
        top.bind("<Button-1>",lambda e:self._dismiss(top)); self.root.after(ms,lambda:self._dismiss(top))
    def _dismiss(self,top):
        try: top.destroy()
        except: pass
        if top in self._toasts: self._toasts.remove(top); self._restack()
    def _restack(self):
        try: rx=self.root.winfo_rootx(); ry=self.root.winfo_rooty(); rw=self.root.winfo_width()
        except: return
        y=16
        for t in self._toasts:
            try:
                t.update_idletasks(); w=t.winfo_width() or 300; h=t.winfo_height() or 72
                t.geometry(f"+{rx+rw-w-18}+{ry+y}"); y+=h+6
            except: pass
    def toggle_panel(self):
        if self._panel and self._panel.winfo_exists(): self._panel.destroy(); self._panel=None; return
        panel=tk.Toplevel(self.root); panel.overrideredirect(True); panel.attributes("-topmost",True)
        panel.configure(bg=T["bg2"],highlightthickness=1,highlightbackground=T["acc"])
        try:
            rx=self.root.winfo_rootx(); ry=self.root.winfo_rooty(); rw=self.root.winfo_width()
            panel.geometry(f"320x460+{rx+rw-338}+{ry+52}")
        except: pass
        self._panel=panel; self._rebuild_panel()
    def _rebuild_panel(self):
        p=self._panel
        if not p or not p.winfo_exists(): return
        for w in p.winfo_children(): w.destroy()
        hdr=tk.Frame(p,bg=T["acc3"],pady=8); hdr.pack(fill="x")
        tk.Label(hdr,text="🔔  Notifications",font=("Segoe UI",11,"bold"),fg=T["text"],bg=T["acc3"]).pack(side="left",padx=12)
        tk.Button(hdr,text="✕",command=lambda:(p.destroy(),setattr(self,"_panel",None)),font=("Segoe UI",8),bg=T["acc3"],fg=T["muted"],relief="flat",cursor="hand2").pack(side="right",padx=8)
        tk.Button(hdr,text="Clear",command=lambda:(self._history.clear(),self._rebuild_panel()),font=("Segoe UI",8),bg=T["acc3"],fg=T["muted"],relief="flat",cursor="hand2").pack(side="right")
        canvas=tk.Canvas(p,bg=T["bg2"],highlightthickness=0)
        vsb=ttk.Scrollbar(p,orient="vertical",command=canvas.yview)
        frame=tk.Frame(canvas,bg=T["bg2"])
        frame.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=frame,anchor="nw"); canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left",fill="both",expand=True); vsb.pack(side="right",fill="y")
        if not self._history:
            tk.Label(frame,text="No notifications yet.",font=("Segoe UI",10),fg=T["muted"],bg=T["bg2"]).pack(pady=30); return
        cols={"info":T["cyan"],"warn":T["yellow"],"error":T["acc"],"ok":T["green"]}
        for n in self._history:
            acc=cols.get(n["kind"],T["cyan"])
            card=tk.Frame(frame,bg=T["bg4"],pady=6); card.pack(fill="x",padx=8,pady=(4,0))
            tk.Label(card,text=f"{n['time']}  {n['title']}",font=("Segoe UI",9,"bold"),fg=acc,bg=T["bg4"],anchor="w").pack(fill="x",padx=10)
            if n["msg"]: tk.Label(card,text=n["msg"],font=("Segoe UI",8),fg=T["muted"],bg=T["bg4"],anchor="w",wraplength=280,justify="left").pack(fill="x",padx=10,pady=(2,0))


# ── In-app dialogs ────────────────────────────────────────
class AppDialog:
    def __init__(self,parent,title,message,buttons=("OK",),icon="ℹ",width=420):
        self.result=None; self._p=parent
        self.overlay=tk.Frame(parent,bg="#000000"); self.overlay.place(x=0,y=0,relwidth=1,relheight=1)
        px=max(10,parent.winfo_width()//2-width//2); py=max(40,parent.winfo_height()//2-120)
        card=tk.Frame(self.overlay,bg=T["bg2"],highlightthickness=2,highlightbackground=T["acc"],width=width)
        card.place(x=px,y=py); card.pack_propagate(False)
        hdr=tk.Frame(card,bg=T["acc3"],pady=10); hdr.pack(fill="x")
        tk.Label(hdr,text=f"{icon}  {title}",font=("Segoe UI",12,"bold"),fg=T["text"],bg=T["acc3"]).pack(padx=16)
        tk.Label(card,text=message,font=("Segoe UI",10),fg=T["text"],bg=T["bg2"],wraplength=width-40,justify="left",pady=16).pack(padx=20,fill="x")
        bf=tk.Frame(card,bg=T["bg2"],pady=12); bf.pack(fill="x",padx=20)
        for t in reversed(buttons):
            def make(txt=t):
                def cmd(): self.result=txt; self.overlay.destroy()
                return cmd
            bg=T["acc"] if t in ("OK","Yes","Confirm","Save","Delete") else T["bg4"]
            tk.Button(bf,text=t,command=make(),font=("Segoe UI",10,"bold"),bg=bg,fg=T["text"],
                      relief="flat",cursor="hand2",padx=14,pady=7,activebackground=T["acc2"]).pack(side="right",padx=4)
    def wait(self): self._p.wait_window(self.overlay); return self.result

class InputDialog:
    def __init__(self,parent,title,prompt,show="",width=380):
        self.result=None; self._p=parent
        px=max(10,parent.winfo_width()//2-width//2); py=max(40,parent.winfo_height()//2-100)
        self.overlay=tk.Frame(parent,bg="#000000"); self.overlay.place(x=0,y=0,relwidth=1,relheight=1)
        card=tk.Frame(self.overlay,bg=T["bg2"],highlightthickness=2,highlightbackground=T["acc"],width=width)
        card.place(x=px,y=py)
        hdr=tk.Frame(card,bg=T["acc3"],pady=8); hdr.pack(fill="x")
        tk.Label(hdr,text=title,font=("Segoe UI",12,"bold"),fg=T["text"],bg=T["acc3"]).pack(padx=16)
        tk.Label(card,text=prompt,font=("Segoe UI",10),fg=T["muted"],bg=T["bg2"]).pack(anchor="w",padx=20,pady=(12,4))
        self.entry=tk.Entry(card,font=("Consolas",11),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                            relief="flat",show=show,highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        self.entry.pack(fill="x",padx=20,ipady=7)
        bf=tk.Frame(card,bg=T["bg2"],pady=12); bf.pack(fill="x",padx=20)
        def cancel(): self.result=None; self.overlay.destroy()
        def confirm(): self.result=self.entry.get(); self.overlay.destroy()
        tk.Button(bf,text="Cancel",command=cancel,font=("Segoe UI",10,"bold"),bg=T["bg4"],fg=T["text"],relief="flat",cursor="hand2",padx=12,pady=6).pack(side="right",padx=4)
        tk.Button(bf,text="OK",command=confirm,font=("Segoe UI",10,"bold"),bg=T["acc"],fg=T["text"],relief="flat",cursor="hand2",padx=12,pady=6).pack(side="right",padx=4)
        self.entry.bind("<Return>",lambda e:confirm()); self.entry.bind("<Escape>",lambda e:cancel())
        self.entry.focus_set()
    def wait(self): self.overlay.wait_window(self.overlay); return self.result


# ══════════════════════════════════════════════════════
# LOGIN WINDOW — P1: no CMD popup, P8: saved logins hover
# ══════════════════════════════════════════════════════
class LoginWindow:
    def __init__(self,app_dir):
        self.app_dir=Path(app_dir); self.result=None
        self.root=tk.Tk(); self.root.title("NexFetch")
        ico=self.app_dir/"assets"/"logo.ico"
        if ico.exists():
            try: self.root.iconbitmap(str(ico))
            except: pass
        self.root.geometry("480x620"); self.root.resizable(False,False)
        self.root.configure(bg=T["bg"]); self.root.protocol("WM_DELETE_WINDOW",sys.exit)
        self._build()

    def _build(self):
        cfg=load_cfg()
        logo_p=self.app_dir/"assets"/"logo.png"
        if logo_p.exists():
            try:
                from PIL import Image,ImageTk
                im=Image.open(logo_p).resize((56,56))
                self._logo=ImageTk.PhotoImage(im)
                tk.Label(self.root,image=self._logo,bg=T["bg"]).pack(pady=(24,0))
            except:
                tk.Label(self.root,text=cfg["tool_name"][0],font=("Segoe UI",36,"bold"),fg=T["acc"],bg=T["bg"]).pack(pady=(24,0))
        else:
            tk.Label(self.root,text=cfg["tool_name"][0],font=("Segoe UI",36,"bold"),fg=T["acc"],bg=T["bg"]).pack(pady=(24,0))
        tk.Label(self.root,text=cfg["tool_name"],font=("Segoe UI",22,"bold"),fg=T["acc"],bg=T["bg"]).pack()
        tk.Label(self.root,text=f"by {cfg['author']}",font=("Segoe UI",9),fg=T["muted"],bg=T["bg"]).pack(pady=(0,18))

        frm=tk.Frame(self.root,bg=T["bg"]); frm.pack(padx=50,fill="x")

        def field(label,show=""):
            tk.Label(frm,text=label,font=("Segoe UI",9,"bold"),fg=T["muted"],bg=T["bg"],anchor="w").pack(fill="x",pady=(8,2))
            e=tk.Entry(frm,font=("Consolas",11),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                       relief="flat",show=show,highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
            e.pack(fill="x",ipady=8); return e

        self.e_user=field("USERNAME")
        self.e_pass=field("PASSWORD","•")

        # P8: Dropdown on focus/hover showing saved logins
        self._setup_autocomplete(frm)

        fp=tk.Label(frm,text="Forgot password?",font=("Segoe UI",9),fg=T["acc"],bg=T["bg"],cursor="hand2")
        fp.pack(anchor="e",pady=(6,0)); fp.bind("<Button-1>",lambda e:self._forgot())
        self.status=tk.Label(frm,text="",font=("Segoe UI",9),fg=T["red"],bg=T["bg"],anchor="w")
        self.status.pack(fill="x",pady=(6,0))

        def sbtn(txt,cmd,color=None):
            bg=color or T["acc"]; fg=T["bg"] if bg==T["acc"] else T["text"]
            tk.Button(frm,text=txt,command=cmd,font=("Segoe UI",11,"bold"),bg=bg,fg=fg,
                      relief="flat",activebackground=T["acc2"],cursor="hand2",pady=10).pack(fill="x",pady=(10,0))

        sbtn("LOGIN",self._login)
        sbtn("CREATE ACCOUNT",self._register,T["bg4"])
        self.e_user.bind("<Return>",lambda e:self.e_pass.focus_set())
        self.e_pass.bind("<Return>",lambda e:self._login())
        self.e_user.focus_set()

    def _setup_autocomplete(self,frm):
        """P8: Saved accounts row — click fills username AND focuses password."""
        saved=load_saved_logins()
        if not saved: return
        sr=tk.Frame(frm,bg=T["bg"]); sr.pack(fill="x",pady=(6,0))
        tk.Label(sr,text="Quick login:",font=("Segoe UI",8),fg=T["muted"],bg=T["bg"]).pack(side="left")
        for s in saved[:6]:
            un=s.get("username","")
            def click_saved(u=un):
                self.e_user.delete(0,"end"); self.e_user.insert(0,u)
                self.e_pass.delete(0,"end")  # clear old password
                self.e_pass.focus_set()      # move focus so user just types password
                # Show a small hint
                self.status.config(text=f"@{u} selected — enter password and press Enter",
                                   fg=T["cyan"])
            b=tk.Button(sr,text=f"@{un}",command=click_saved,
                        font=("Segoe UI",8,"bold"),bg=T["bg4"],fg=T["acc"],
                        relief="flat",cursor="hand2",padx=8,pady=4)
            b.pack(side="left",padx=(4,0))
            b.bind("<Enter>",lambda e,btn=b:btn.config(bg=T["acc3"]))
            b.bind("<Leave>",lambda e,btn=b:btn.config(bg=T["bg4"]))

    def _login(self):
        u=self.e_user.get().strip(); p=self.e_pass.get()
        if not u or not p: self.status.config(text="Enter username and password."); return
        users=load_users()
        if u not in users: self.status.config(text="Account not found."); return
        if users[u]["pw"]!=hpw(p): self.status.config(text="Incorrect password."); return
        saved=[s for s in load_saved_logins() if s.get("username")!=u]
        saved.insert(0,{"username":u}); save_saved_logins(saved)
        self.result=u; self.root.destroy()

    def _forgot(self):
        u=self.e_user.get().strip(); users=load_users()
        if not u or u not in users: self.status.config(text="Enter your username first."); return
        win=tk.Toplevel(self.root); win.title("Password Recovery"); win.geometry("480x320")
        win.configure(bg=T["bg2"]); win.grab_set()
        tk.Label(win,text="Password Recovery",font=("Segoe UI",14,"bold"),fg=T["acc"],bg=T["bg2"]).pack(pady=(20,4))
        tk.Label(win,
                 text="Enter your 12-word recovery phrase\n(comma or space separated, as shown when you created your account).",
                 font=("Segoe UI",9),fg=T["muted"],bg=T["bg2"],justify="left",wraplength=420).pack(padx=20,pady=(0,8))
        phrase_e=tk.Text(win,height=3,font=("Consolas",9),bg=T["bg4"],fg=T["text"],
                         insertbackground=T["acc"],relief="flat",wrap="word",
                         highlightthickness=1,highlightbackground=T["border"])
        phrase_e.pack(fill="x",padx=20,pady=(0,6))
        hint=users[u].get("pw_hint","")
        if hint: tk.Label(win,text=f"Hint: {hint}",font=("Segoe UI",9),fg=T["yellow"],bg=T["bg2"]).pack(padx=20,anchor="w")
        st=tk.Label(win,text="",font=("Segoe UI",9),fg=T["red"],bg=T["bg2"]); st.pack(padx=20,anchor="w")
        def validate():
            entered=[w.strip().lower() for w in re.split(r'[,\s]+',phrase_e.get("1.0","end").strip()) if w.strip()]
            stored=[w.strip().lower() for w in re.split(r'[,\s]+',users[u].get("recovery_phrases","")) if w.strip()]
            if entered==stored and len(entered)>=8:
                st.config(text="✅ Verified!",fg=T["green"]); win.after(800,lambda:(win.destroy(),self._reset_password(u)))
            else: st.config(text="❌ Phrase does not match. Check and try again.")
        tk.Button(win,text="Verify Phrase",command=validate,font=("Segoe UI",10,"bold"),bg=T["acc"],fg=T["text"],relief="flat",cursor="hand2",pady=8).pack(padx=20,pady=(8,0),fill="x")

    def _reset_password(self,u):
        win=tk.Toplevel(self.root); win.title("Reset Password"); win.geometry("420x240"); win.configure(bg=T["bg2"]); win.grab_set()
        tk.Label(win,text="Set New Password",font=("Segoe UI",14,"bold"),fg=T["acc"],bg=T["bg2"]).pack(pady=(20,4))
        frm=tk.Frame(win,bg=T["bg2"]); frm.pack(padx=20,fill="x",pady=8)
        def ef(lbl,show=""):
            tk.Label(frm,text=lbl,font=("Segoe UI",9,"bold"),fg=T["text"],bg=T["bg2"]).pack(anchor="w")
            e=tk.Entry(frm,font=("Consolas",11),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                       relief="flat",show=show,highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
            e.pack(fill="x",ipady=7,pady=(2,8)); return e
        e1=ef("New password:","•"); e2=ef("Confirm:","•")
        st=tk.Label(frm,text="",font=("Segoe UI",9),fg=T["red"],bg=T["bg2"]); st.pack(anchor="w")
        def do():
            p1=e1.get(); p2=e2.get()
            if len(p1)<4: st.config(text="Min 4 chars."); return
            if p1!=p2: st.config(text="Passwords don't match."); return
            users=load_users(); users[u]["pw"]=hpw(p1); save_users(users)
            win.destroy(); self.e_pass.delete(0,"end"); self.e_pass.insert(0,p1)
            self.e_user.delete(0,"end"); self.e_user.insert(0,u); self._login()
        tk.Button(frm,text="Reset Password",command=do,font=("Segoe UI",10,"bold"),bg=T["acc"],fg=T["text"],relief="flat",cursor="hand2",pady=8).pack(fill="x")
        e1.focus_set()

    def _register(self):
        # P1: No CMD popup — this is all in-process; no subprocess called here
        win=tk.Toplevel(self.root); win.title("Create Account"); win.geometry("480x640")
        win.configure(bg=T["bg"]); win.grab_set()
        tk.Label(win,text="Create Account",font=("Segoe UI",18,"bold"),fg=T["acc"],bg=T["bg"]).pack(pady=(22,4))
        tk.Label(win,text="Admin invite code required.",font=("Segoe UI",9),fg=T["muted"],bg=T["bg"]).pack()
        frm=tk.Frame(win,bg=T["bg"]); frm.pack(padx=36,fill="x",pady=8)
        entries={}
        # P1: No "ADDRESS/LOCATION" field
        for label,key,show in [
            ("FULL NAME","full_name",""),("USERNAME","username",""),
            ("EMAIL","email",""),
            ("PASSWORD","password","•"),("CONFIRM PASSWORD","confirm","•"),
            ("ADMIN INVITE CODE","invite_code","•"),
        ]:
            tk.Label(frm,text=label,font=("Segoe UI",9,"bold"),fg=T["muted"],bg=T["bg"],anchor="w").pack(fill="x",pady=(8,2))
            e=tk.Entry(frm,font=("Consolas",10),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                       relief="flat",show=show,highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
            e.pack(fill="x",ipady=6); entries[key]=e
        st=tk.Label(frm,text="",font=("Segoe UI",9),fg=T["red"],bg=T["bg"],anchor="w"); st.pack(fill="x",pady=(6,0))

        def do_reg():
            v={k:e.get().strip() for k,e in entries.items()}
            v["password"]=entries["password"].get(); v["confirm"]=entries["confirm"].get()
            if not all([v["full_name"],v["username"],v["email"],v["password"],v["invite_code"]]):
                st.config(text="All fields required."); return
            if len(v["username"])<3: st.config(text="Username min 3 chars."); return
            if len(v["password"])<4: st.config(text="Password min 4 chars."); return
            if v["password"]!=v["confirm"]: st.config(text="Passwords don't match."); return
            if re.search(r'[^a-zA-Z0-9_\-]',v["username"]): st.config(text="Username: letters/numbers/_ only."); return
            cfg=load_cfg(); codes=cfg.get("invite_codes",["NEXFETCH2024"])
            if isinstance(codes,str): codes=[codes]
            if v["invite_code"] not in codes: st.config(text="Invalid invite code."); return
            users=load_users()
            if v["username"] in users: st.config(text="Username taken."); return
            phrases=" ".join(random.choices(["apple","ocean","river","mountain","forest","thunder",
                "crystal","shadow","falcon","storm","ember","silver","golden","cosmic","nexus","cipher",
                "breeze","hollow","prism","vortex","lantern","marble","cobalt","zenith"],k=12))
            role="user"
            if not cfg.get("admin_username",""):
                role="admin"; cfg["admin_username"]=v["username"]; save_cfg(cfg)
            users[v["username"]]={
                "pw":hpw(v["password"]),"pw_hint":"","role":role,
                "full_name":v["full_name"],"display_name":v["full_name"],
                "email":v["email"],"bio":"","phone":"","dob":"","avatar":"",
                "recovery_phrases":phrases,"notes":"","created":datetime.datetime.now().isoformat(),
            }
            save_users(users); udir(v["username"])
            # Show phrases — no subprocess, no CMD
            w2=tk.Toplevel(win); w2.title("IMPORTANT!"); w2.geometry("500x300"); w2.configure(bg=T["bg2"]); w2.grab_set()
            tk.Label(w2,text="✅ Account Created!",font=("Segoe UI",14,"bold"),fg=T["green"],bg=T["bg2"]).pack(pady=14)
            tk.Label(w2,text="⚠  WRITE THESE DOWN NOW — you can't recover them later!",
                     font=("Segoe UI",9,"bold"),fg=T["yellow"],bg=T["bg2"],wraplength=460).pack(padx=20)
            pb=tk.Text(w2,height=3,font=("Consolas",10),bg=T["bg4"],fg=T["yellow"],relief="flat",wrap="word")
            pb.insert("1.0",phrases); pb.configure(state="disabled"); pb.pack(fill="x",padx=20,pady=(8,4))
            # P9: right-click on phrases to copy
            def copy_phrases():
                w2.clipboard_clear(); w2.clipboard_append(phrases)
            rm=tk.Menu(pb,tearoff=0,bg=T["bg2"],fg=T["text"])
            rm.add_command(label="📋 Copy phrases",command=copy_phrases)
            pb.bind("<Button-3>",lambda e:rm.post(e.x_root,e.y_root))
            tk.Button(w2,text="I've saved my phrases — Continue",
                      command=lambda:(w2.destroy(),win.destroy(),self._autologin(v["username"],v["password"])),
                      font=("Segoe UI",10,"bold"),bg=T["acc"],fg=T["text"],relief="flat",cursor="hand2",pady=8).pack(padx=20,pady=(8,0),fill="x")

        tk.Button(frm,text="CREATE ACCOUNT",command=do_reg,
                  font=("Segoe UI",11,"bold"),bg=T["acc"],fg=T["text"],
                  relief="flat",cursor="hand2",pady=10).pack(fill="x",pady=(14,0))

    def _autologin(self,u,p):
        self.e_user.delete(0,"end"); self.e_user.insert(0,u)
        self.e_pass.delete(0,"end"); self.e_pass.insert(0,p); self._login()

    def run(self): self.root.mainloop(); return self.result


# ══════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════
class NexFetchApp:
    def __init__(self,username,app_dir):
        self.username=username; self.app_dir=Path(app_dir)
        self.udir_=udir(username); self.cfg=load_cfg(); self._load_ucfg()
        self.root=tk.Tk(); self.root.title(f"NexFetch  ·  @{username}")
        self.root.geometry("1060x780"); self.root.minsize(980,680); self.root.configure(bg=T["bg"])
        self._set_icon(); self.notif=NotifCenter(self.root)
        # Start web server
        self._web_port=None
        if _start_web_server:
            try:
                self._web_port=_start_web_server(self.app_dir,self.cfg.get('dl_path',str(Path.home()/'Downloads'/'NexFetch')))
            except Exception: pass
        self._dl_paused=threading.Event(); self._dl_stop=threading.Event()
        self._mu_paused=threading.Event(); self._mu_stop=threading.Event()
        self._dl_q=[]; self._mu_q=[]; self._scraped=[]; self._ec_prods=[]
        self._ig_loader=None; self._dl_t0=None; self._pending_n=[]
        self._load_q(); self._styles(); self._ui()

    def _load_ucfg(self):
        f=self.udir_/"config.json"
        if f.exists():
            try: self.cfg.update(json.loads(f.read_text("utf-8")))
            except: pass
        if not self.cfg.get("dl_path"): self.cfg["dl_path"]=str(Path.home()/"Downloads"/"NexFetch")

    def _save_ucfg(self):
        (self.udir_/"config.json").write_text(json.dumps({"dl_path":self.cfg.get("dl_path","")},indent=2),"utf-8")

    def _set_icon(self):
        for p in [self.cfg.get("logo_path",""),str(self.app_dir/"assets"/"logo.ico"),str(self.app_dir/"assets"/"logo.png")]:
            if p and Path(p).exists():
                try:
                    if p.endswith(".ico"): self.root.iconbitmap(p); return
                    from PIL import Image,ImageTk
                    im=Image.open(p).resize((32,32)); self._icon=ImageTk.PhotoImage(im)
                    self.root.iconphoto(True,self._icon); return
                except: pass

    def _load_q(self):
        qf=self.udir_/"queue.json"
        if qf.exists():
            try:
                d=json.loads(qf.read_text("utf-8"))
                self._dl_q=[i for i in d.get("dl",[]) if i.get("status") in ("pending","paused")]
                self._mu_q=[i for i in d.get("mu",[]) if i.get("status") in ("pending","paused")]
                self._pending_n=d.get("notifs",[])
            except: pass

    def _save_q(self,n=None):
        if n: self._pending_n.append(n)
        try: (self.udir_/"queue.json").write_text(json.dumps({"dl":self._dl_q,"mu":self._mu_q,"notifs":self._pending_n[-30:]},indent=2),"utf-8")
        except: pass

    def _styles(self):
        try:
            s=ttk.Style()
            try: s.theme_use("clam")
            except: pass
            for cfg_call in [
                lambda:s.configure("TNotebook",background=T["bg"],borderwidth=0,tabmargins=0),
                lambda:s.configure("TNotebook.Tab",background=T["bg2"],foreground=T["muted"],padding=[20,10],font=("Segoe UI",10,"bold"),borderwidth=0),
                lambda:s.map("TNotebook.Tab",background=[("selected",T["bg3"])],foreground=[("selected",T["acc"])]),
                lambda:s.configure("TProgressbar",troughcolor=T["bg2"],background=T["acc"],thickness=8,relief="flat"),
                lambda:s.configure("TCombobox",fieldbackground=T["bg4"],background=T["bg4"],foreground=T["text"],selectbackground=T["acc3"],borderwidth=0),
                lambda:s.map("TCombobox",fieldbackground=[("readonly",T["bg4"])]),
            ]:
                try: cfg_call()
                except: pass
        except: pass

    def _FF(self): return ("Consolas",self.cfg.get("font_size",9))
    def _F(self,sz=10,b=False): return (self.cfg.get("font_family","Segoe UI"),sz,"bold" if b else "normal")
    def _ff_exe(self):
        d=self.app_dir/"ffmpeg_bin"; return str(d/"ffmpeg.exe") if (d/"ffmpeg.exe").exists() else "ffmpeg"
    def _ff_dir_arg(self):
        d=self.app_dir/"ffmpeg_bin"; return ["--ffmpeg-location",str(d)] if (d/"ffmpeg.exe").exists() else []

    def _ui(self):
        users=load_users(); self._role=users.get(self.username,{}).get("role","user")
        bg_p=self.cfg.get("bg_image","")
        if bg_p and Path(bg_p).exists():
            try:
                from PIL import Image,ImageTk
                if bg_p.lower().endswith(".gif"):
                    self._gif_lbl=tk.Label(self.root); self._gif_lbl.place(x=0,y=0,relwidth=1,relheight=1)
                    self._gif_f=[]; gif=Image.open(bg_p)
                    try:
                        while True:
                            self._gif_f.append(ImageTk.PhotoImage(gif.copy().resize((1060,780)))); gif.seek(gif.tell()+1)
                    except EOFError: pass
                    def anim(i=0):
                        if self._gif_f: self._gif_lbl.configure(image=self._gif_f[i]); self.root.after(80,anim,(i+1)%len(self._gif_f))
                    anim()
                else:
                    im=Image.open(bg_p).resize((1060,780)); self._bgi=ImageTk.PhotoImage(im)
                    tk.Label(self.root,image=self._bgi).place(x=0,y=0,relwidth=1,relheight=1)
            except: pass

        # Header
        hdr=tk.Frame(self.root,bg=T["bg2"]); hdr.pack(fill="x")
        ih=tk.Frame(hdr,bg=T["bg2"]); ih.pack(fill="x",padx=20,pady=8)
        lp=self.cfg.get("logo_path","") or str(self.app_dir/"assets"/"logo.png")
        if Path(lp).exists():
            try:
                from PIL import Image,ImageTk
                im=Image.open(lp).resize((32,32)); self._hlogo=ImageTk.PhotoImage(im)
                tk.Label(ih,image=self._hlogo,bg=T["bg2"]).pack(side="left",padx=(0,8))
            except: pass
        tk.Label(ih,text=self.cfg["tool_name"],font=("Segoe UI",16,"bold"),fg=T["acc"],bg=T["bg2"]).pack(side="left")
        tk.Label(ih,text=f"  v{self.cfg['version']}",font=self._F(9),fg=T["muted"],bg=T["bg2"]).pack(side="left",pady=(4,0))

        right=tk.Frame(ih,bg=T["bg2"]); right.pack(side="right")

        # P6: Avatar + username in header, next to notification bell
        ud=users.get(self.username,{})
        av_path=ud.get("avatar","")
        self._hdr_av_lbl=tk.Label(right,bg=T["bg2"])
        self._hdr_av_lbl.pack(side="left",padx=(0,6))
        self._load_hdr_avatar(av_path)

        badge="👑" if self._role=="admin" else ""
        uname_lbl=tk.Label(right,text=f"{badge} @{self.username}",font=("Segoe UI",9,"bold"),fg=T["acc"],bg=T["bg2"])
        uname_lbl.pack(side="left",padx=(0,8))

        tk.Button(right,text="🔔",font=("Segoe UI",13),bg=T["bg2"],fg=T["acc"],relief="flat",cursor="hand2",command=self.notif.toggle_panel).pack(side="left",padx=(0,6))
        ub=tk.Frame(right,bg=T["bg4"],padx=8,pady=4); ub.pack(side="left")
        tk.Button(ub,text="⇄ Switch",command=self._switch_safe,font=("Segoe UI",9),bg=T["bg4"],fg=T["muted"],relief="flat",cursor="hand2",padx=6).pack()
        tk.Button(right,text="🌐",command=self._open_web_ui,
                  font=("Segoe UI",12),bg=T["bg2"],fg=T["cyan"],
                  relief="flat",cursor="hand2",padx=6).pack(side="left",padx=(6,0))

        tk.Frame(self.root,bg=T["acc"],height=2).pack(fill="x")

        nb=ttk.Notebook(self.root); nb.pack(fill="both",expand=True)
        self._tab_dl(nb); self._tab_music(nb); self._tab_scraper(nb)
        self._tab_ecomm(nb); self._tab_account(nb); self._tab_settings(nb)

        # P9: Global mousewheel scroll
        self.root.bind_all("<MouseWheel>",self._on_mousewheel)
        self.root.bind_all("<Button-4>",lambda e:self._on_scroll_up(e))
        self.root.bind_all("<Button-5>",lambda e:self._on_scroll_down(e))

        if self._pending_n: self.root.after(1200,self._show_pending)
        if self._dl_q or self._mu_q:
            self.root.after(900,lambda:self.notif.push("Queue Restored",f"{len(self._dl_q)} video(s), {len(self._mu_q)} music track(s)","info"))
        self.root.protocol("WM_DELETE_WINDOW",self._on_close)

    def _on_mousewheel(self,event):
        """P9: Route mousewheel to focused/hovered widget."""
        try:
            w=event.widget
            while w:
                if isinstance(w,(tk.Canvas,scrolledtext.ScrolledText,tk.Text)):
                    try: w.yview_scroll(int(-1*(event.delta/120)),"units")
                    except: pass
                    return
                try: w=w.master
                except: break
        except: pass

    def _on_scroll_up(self,event):
        try: event.widget.yview_scroll(-1,"units")
        except: pass

    def _on_scroll_down(self,event):
        try: event.widget.yview_scroll(1,"units")
        except: pass

    def _load_hdr_avatar(self,path):
        """P6: Show small 28x28 avatar in header."""
        if path and Path(path).exists():
            try:
                from PIL import Image,ImageTk
                im=Image.open(path).resize((28,28)); self._hdr_img=ImageTk.PhotoImage(im)
                self._hdr_av_lbl.config(image=self._hdr_img,text=""); return
            except: pass
        self._hdr_av_lbl.config(image="",text="◎",font=("Segoe UI",16),fg=T["acc"],bg=T["bg2"])

    def _show_pending(self):
        for n in self._pending_n[-4:]: self.notif.push(n.get("title",""),n.get("msg",""),n.get("kind","info"))
        self._pending_n.clear(); self._save_q()

    def _on_close(self):
        self._dl_stop.set(); self._mu_stop.set(); self._save_q(); self.root.destroy()

    def _open_web_ui(self):
        """Open the web UI in the browser."""
        import webbrowser
        if self._web_port:
            webbrowser.open(f'http://127.0.0.1:{self._web_port}')
            self.notif.push('Web UI','Opening in browser — downloads go to your folder.','info')
        else:
            AppDialog(self.root,'Web Server','Web server failed to start. Check START_DEBUG.bat for errors.',('OK',),'⚠').wait()

    def _switch_safe(self):
        """P7: Toplevel overlay — root stays visible, no blank screen ever."""
        d=AppDialog(self.root,"Switch User","Save and switch account?",("Cancel","Switch"),"⇄")
        if d.wait()!="Switch": return
        self._save_q(); self._dl_stop.set(); self._mu_stop.set()
        app_dir=self.app_dir; result_holder=[None]

        overlay=tk.Toplevel(self.root)
        overlay.title("Switch Account"); overlay.geometry("480x560")
        overlay.resizable(False,False); overlay.configure(bg=T["bg"]); overlay.grab_set()
        ico=app_dir/"assets"/"logo.ico"
        if ico.exists():
            try: overlay.iconbitmap(str(ico))
            except: pass

        cfg=load_cfg()
        logo_p=app_dir/"assets"/"logo.png"
        if logo_p.exists():
            try:
                from PIL import Image,ImageTk
                im=Image.open(logo_p).resize((44,44)); _img=ImageTk.PhotoImage(im); overlay._img=_img
                tk.Label(overlay,image=_img,bg=T["bg"]).pack(pady=(20,0))
            except:
                tk.Label(overlay,text=cfg["tool_name"][0],font=("Segoe UI",28,"bold"),fg=T["acc"],bg=T["bg"]).pack(pady=(20,0))
        else:
            tk.Label(overlay,text=cfg["tool_name"][0],font=("Segoe UI",28,"bold"),fg=T["acc"],bg=T["bg"]).pack(pady=(20,0))
        tk.Label(overlay,text="Switch Account",font=("Segoe UI",16,"bold"),fg=T["acc"],bg=T["bg"]).pack()
        tk.Label(overlay,text="Log into a different account",font=("Segoe UI",9),fg=T["muted"],bg=T["bg"]).pack(pady=(0,14))

        frm=tk.Frame(overlay,bg=T["bg"]); frm.pack(padx=44,fill="x")
        tk.Label(frm,text="USERNAME",font=("Segoe UI",9,"bold"),fg=T["muted"],bg=T["bg"],anchor="w").pack(fill="x",pady=(8,2))
        eu=tk.Entry(frm,font=("Consolas",11),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                    relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        eu.pack(fill="x",ipady=8)
        tk.Label(frm,text="PASSWORD",font=("Segoe UI",9,"bold"),fg=T["muted"],bg=T["bg"],anchor="w").pack(fill="x",pady=(10,2))
        ep=tk.Entry(frm,font=("Consolas",11),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                    relief="flat",show="•",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        ep.pack(fill="x",ipady=8)
        # Saved logins
        saved=load_saved_logins()
        if saved:
            sr=tk.Frame(frm,bg=T["bg"]); sr.pack(fill="x",pady=(6,0))
            tk.Label(sr,text="Saved:",font=("Segoe UI",8),fg=T["muted"],bg=T["bg"]).pack(side="left")
            for s in saved[:5]:
                un=s.get("username","")
                def ql(u=un): eu.delete(0,"end"); eu.insert(0,u); ep.focus_set()
                b=tk.Button(sr,text=f"@{un}",command=ql,font=("Segoe UI",8,"bold"),bg=T["bg4"],fg=T["acc"],relief="flat",cursor="hand2",padx=8,pady=3); b.pack(side="left",padx=(4,0))
                b.bind("<Enter>",lambda e,btn=b:btn.config(bg=T["acc3"]))
                b.bind("<Leave>",lambda e,btn=b:btn.config(bg=T["bg4"]))
        st=tk.Label(frm,text="",font=("Segoe UI",9),fg=T["red"],bg=T["bg"],anchor="w"); st.pack(fill="x",pady=(6,0))

        def do_login():
            u=eu.get().strip(); p=ep.get()
            if not u or not p: st.config(text="Enter credentials."); return
            users=load_users()
            if u not in users: st.config(text="Account not found."); return
            if users[u]["pw"]!=hpw(p): st.config(text="Wrong password."); return
            sv=[s for s in load_saved_logins() if s.get("username")!=u]
            sv.insert(0,{"username":u}); save_saved_logins(sv)
            result_holder[0]=u; overlay.destroy()

        tk.Button(frm,text="SWITCH ACCOUNT",command=do_login,font=("Segoe UI",11,"bold"),bg=T["acc"],fg=T["bg"],relief="flat",activebackground=T["acc2"],cursor="hand2",pady=10).pack(fill="x",pady=(12,0))
        tk.Button(frm,text="CANCEL",command=overlay.destroy,font=("Segoe UI",11,"bold"),bg=T["bg4"],fg=T["text"],relief="flat",cursor="hand2",pady=10).pack(fill="x",pady=(8,0))
        eu.bind("<Return>",lambda e:ep.focus_set()); ep.bind("<Return>",lambda e:do_login()); eu.focus_set()

        self.root.wait_window(overlay)
        new_user=result_holder[0]
        if new_user:
            self.root.after(80,lambda:self._do_handoff(new_user,app_dir))

    def _do_handoff(self,new_user,app_dir):
        """P7: No blank screen — withdraw then destroy on next loop tick."""
        try: self.root.withdraw()
        except: pass
        def _finish():
            try: self.root.destroy()
            except: pass
            # Small sleep lets the OS clean up the old window
            import time as _t; _t.sleep(0.08)
            NexFetchApp(new_user, app_dir).run()
        threading.Thread(target=_finish, daemon=False).start()

    # ── Widget helpers ────────────────────────────────────
    def _sec(self,p,title,sub=""):
        tk.Label(p,text=title,font=("Segoe UI",14,"bold"),fg=T["acc"],bg=T["bg3"]).pack(anchor="w",padx=22,pady=(16,0))
        if sub: tk.Label(p,text=sub,font=self._F(9),fg=T["muted"],bg=T["bg3"],wraplength=980,justify="left").pack(anchor="w",padx=22)
        tk.Frame(p,bg=T["acc3"],height=1).pack(fill="x",padx=22,pady=(4,8))

    def _lbl(self,p,text,side="top"):
        l=tk.Label(p,text=text,font=self._F(10,True),fg=T["text"],bg=T["bg3"])
        if side=="top": l.pack(anchor="w",padx=22,pady=(4,2))
        else: l.pack(side=side,padx=4)
        return l

    def _entry(self,p,default=""):
        e=tk.Entry(p,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                   relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        e.insert(0,default); e.pack(fill="x",padx=22,pady=(0,4),ipady=6); self._rc(e); return e

    def _enil(self,p,default=""):
        e=tk.Entry(p,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                   relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        e.insert(0,default); e.pack(side="left",fill="x",expand=True,padx=4,ipady=5); self._rc(e); return e

    def _textbox(self,p,h=5):
        b=tk.Text(p,height=h,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                  relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        b.pack(fill="x",padx=22,pady=(0,4)); self._rct(b); return b

    def _logbox(self,p,h=8):
        b=scrolledtext.ScrolledText(p,height=h,font=self._FF(),bg=T["log_bg"],fg=T["log_fg"],
                                    insertbackground=T["acc"],relief="flat",state="disabled")
        b.pack(fill="both",expand=True,padx=22,pady=(0,8)); self._rct(b); return b

    def _mkbar(self,p,mode="determinate"):
        bar=ttk.Progressbar(p,mode=mode,maximum=100); bar.pack(fill="x",padx=22,pady=(4,0)); return bar

    def _btn(self,p,text,cmd,full=False,sm=False,color=None,side="top"):
        bg=color or T["acc"]; fg=T["bg"] if bg in (T["acc"],T["yellow"],T["green"],T["cyan"]) else T["text"]
        b=tk.Button(p,text=text,command=cmd,
                    font=("Segoe UI",9,"bold") if sm else ("Segoe UI",10,"bold"),
                    bg=bg,fg=fg,relief="flat",activebackground=T["acc2"],activeforeground=T["text"],
                    cursor="hand2",pady=3 if sm else 8,padx=8 if sm else 20)
        if full: b.pack(fill="x",padx=22,pady=(5,3),ipady=2)
        elif side!="top": b.pack(side=side,padx=3)
        else: b.pack(anchor="w",padx=22,pady=3)
        return b

    def _sh(self,p,t):
        tk.Label(p,text=t,font=("Segoe UI",11,"bold"),fg=T["acc"],bg=T["bg3"]).pack(anchor="w",padx=22,pady=(14,2))
        tk.Frame(p,bg=T["acc3"],height=1).pack(fill="x",padx=22,pady=(0,6))

    def _log(self,box,msg):
        ts=datetime.datetime.now().strftime("%H:%M:%S")
        def _d():
            box.configure(state="normal"); box.insert("end",f"[{ts}] {msg}\n"); box.see("end"); box.configure(state="disabled")
        self.root.after(0,_d)

    def _run_cmd(self,cmd,box):
        try:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  text=True,encoding="utf-8",errors="replace",creationflags=FLAGS)
            for line in proc.stdout:
                l=line.rstrip()
                if l: self._log(box,l)
            proc.wait()
        except FileNotFoundError: self._log(box,f"❌ Not found: {cmd[0]}")
        except Exception as e: self._log(box,f"❌ {e}")

    def _rc(self,w):
        """P9: Right-click paste on every Entry widget."""
        m=tk.Menu(w,tearoff=0,bg=T["bg2"],fg=T["text"],activebackground=T["acc"],activeforeground=T["bg"],font=("Segoe UI",9))
        def paste():
            try: w.delete(0,"end"); w.insert(0,self.root.clipboard_get())
            except: pass
        def paste_append():
            try: w.insert(tk.END,self.root.clipboard_get())
            except: pass
        m.add_command(label="📋 Paste",command=paste)
        m.add_command(label="📋 Paste (append)",command=paste_append)
        m.add_command(label="📄 Copy",command=lambda:(self.root.clipboard_clear(),self.root.clipboard_append(w.get())))
        m.add_command(label="✂ Cut",command=lambda:(self.root.clipboard_clear(),self.root.clipboard_append(w.get()),w.delete(0,"end")))
        m.add_separator()
        m.add_command(label="🗑 Clear",command=lambda:w.delete(0,"end"))
        m.add_command(label="📂 Open folder",command=lambda:self._open_f(w.get()))
        w.bind("<Button-3>",lambda e:m.post(e.x_root,e.y_root))

    def _rct(self,w):
        """P9: Right-click paste on every Text widget."""
        m=tk.Menu(w,tearoff=0,bg=T["bg2"],fg=T["text"],activebackground=T["acc"],activeforeground=T["bg"],font=("Segoe UI",9))
        def paste():
            try: w.configure(state="normal"); w.insert(tk.INSERT,self.root.clipboard_get())
            except: pass
        m.add_command(label="📋 Paste",command=paste)
        m.add_command(label="📄 Copy All",command=lambda:(self.root.clipboard_clear(),self.root.clipboard_append(w.get("1.0","end").strip())))
        m.add_separator()
        m.add_command(label="🗑 Clear",command=lambda:(w.configure(state="normal"),w.delete("1.0","end")))
        w.bind("<Button-3>",lambda e:m.post(e.x_root,e.y_root))

    def _toggle(self,e): e.config(show="" if e.cget("show")=="•" else "•")
    def _open_f(self,p):
        if not p: return
        os.makedirs(p,exist_ok=True)
        if sys.platform=="win32":
            try: os.startfile(p)
            except: pass

    def _browse_dir(self,e):
        p=filedialog.askdirectory()
        if p: e.delete(0,"end"); e.insert(0,p)

    def _browse_file(self,e,ft):
        p=filedialog.askopenfilename(filetypes=ft)
        if p: e.delete(0,"end"); e.insert(0,p)

    def _scrolled_frame(self,parent):
        canvas=tk.Canvas(parent,bg=T["bg3"],highlightthickness=0)
        vsb=ttk.Scrollbar(parent,orient="vertical",command=canvas.yview)
        inner=tk.Frame(canvas,bg=T["bg3"])
        inner.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=inner,anchor="nw"); canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left",fill="both",expand=True); vsb.pack(side="right",fill="y")
        # P9: mousewheel on scrolled frames
        def _scroll(e):
            canvas.yview_scroll(int(-1*(e.delta/120)),"units")
        canvas.bind("<MouseWheel>",_scroll); inner.bind("<MouseWheel>",_scroll)
        return inner

    # ── TAB 1: DOWNLOAD + IMAGES — P2 ────────────────────
    def _tab_dl(self,nb):
        f=tk.Frame(nb,bg=T["bg3"]); nb.add(f,text="  📥 Download  ")
        self._sec(f,"Universal Downloader",
                  "Videos · Images · Audio — YouTube · Instagram · Facebook · TikTok · Twitter · 1000+ sites")

        # URL box
        self._lbl(f,"Paste URL(s) — one per line (video, image post, or gallery):")
        self.dl_urls=self._textbox(f,4)

        # Format + Quality row
        row=tk.Frame(f,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=(4,0))
        self._lbl(row,"Format:","left")
        self.dl_fmt=ttk.Combobox(row,values=["mp4 (video)","mp3 (audio)","images only","best (auto)","mkv","webm","m4a","opus","wav"],width=16,state="readonly")
        self.dl_fmt.set("mp4 (video)"); self.dl_fmt.pack(side="left",padx=(4,20))
        self.dl_fmt.bind("<<ComboboxSelected>>",self._dl_fmt_ch)
        self._lbl(row,"Quality:","left")
        self.dl_qual=ttk.Combobox(row,values=["1080p","720p","480p","360p","240p","best"],width=12,state="readonly")
        self.dl_qual.set("720p"); self.dl_qual.pack(side="left",padx=(4,0))

        # P2: Clip section — start-end time + ratio
        clip_frame=tk.LabelFrame(f,text="  ✂ Clip Download (optional — leave blank for full video)  ",
                                  font=("Segoe UI",9,"bold"),fg=T["acc"],bg=T["bg3"],bd=1,relief="groove")
        clip_frame.pack(fill="x",padx=22,pady=(8,0))
        cr=tk.Frame(clip_frame,bg=T["bg3"]); cr.pack(fill="x",padx=12,pady=(8,8))
        tk.Label(cr,text="Start time:",font=self._F(9,True),fg=T["text"],bg=T["bg3"]).pack(side="left")
        self.dl_start=tk.Entry(cr,font=("Consolas",10),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                               relief="flat",width=10,highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        self.dl_start.insert(0,""); self.dl_start.pack(side="left",ipady=5,padx=(4,16))
        tk.Label(cr,text="End time:",font=self._F(9,True),fg=T["text"],bg=T["bg3"]).pack(side="left")
        self.dl_end=tk.Entry(cr,font=("Consolas",10),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                             relief="flat",width=10,highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        self.dl_end.insert(0,""); self.dl_end.pack(side="left",ipady=5,padx=(4,16))
        tk.Label(cr,text="Format: 2:00 or 2:00-2:30 in Start,  2:30 in End",
                 font=self._F(8),fg=T["muted"],bg=T["bg3"]).pack(side="left")
        cr2=tk.Frame(clip_frame,bg=T["bg3"]); cr2.pack(fill="x",padx=12,pady=(0,8))
        tk.Label(cr2,text="Ratio:",font=self._F(9,True),fg=T["text"],bg=T["bg3"]).pack(side="left")
        self.dl_ratio=ttk.Combobox(cr2,values=["original","16:9","9:16 (vertical)","1:1 (square)","4:3"],width=18,state="readonly")
        self.dl_ratio.set("original"); self.dl_ratio.pack(side="left",padx=(4,0))

        fr=tk.Frame(f,bg=T["bg3"]); fr.pack(fill="x",padx=22,pady=(8,0))
        self._lbl(fr,"Save to:","left")
        self.dl_path=self._enil(fr,self.cfg["dl_path"]+"/Videos")
        self._btn(fr,"📁",lambda:self._browse_dir(self.dl_path),sm=True,side="left")
        self._btn(fr,"📂",lambda:self._open_f(self.dl_path.get()),sm=True,side="left")

        brow=tk.Frame(f,bg=T["bg3"]); brow.pack(fill="x",padx=22,pady=(8,2))
        self._btn(brow,"⬇  Add & Download",self._dl_add,side="left",color=T["acc"])
        self._btn(brow,"⏸",self._dl_pause,sm=True,side="left",color=T["yellow"])
        self._btn(brow,"▶ Resume",self._dl_resume,sm=True,side="left",color=T["cyan"])
        self._btn(brow,"🗑",self._dl_clear,sm=True,side="left",color=T["red"])

        srow=tk.Frame(f,bg=T["bg3"]); srow.pack(fill="x",padx=22,pady=(4,0))
        self.dl_stats=tk.StringVar(value="Queue: 0  |  Done: 0  |  Failed: 0")
        self.dl_eta=tk.StringVar(value="")
        tk.Label(srow,textvariable=self.dl_stats,font=self._F(9),fg=T["acc"],bg=T["bg3"]).pack(side="left")
        tk.Label(srow,textvariable=self.dl_eta,font=self._F(9,True),fg=T["yellow"],bg=T["bg3"]).pack(side="right")
        self.dl_bar=self._mkbar(f); self.dl_bar_lbl=tk.StringVar(value="")
        tk.Label(f,textvariable=self.dl_bar_lbl,font=self._F(8),fg=T["muted"],bg=T["bg3"]).pack(anchor="w",padx=22)
        self._lbl(f,"Log:"); self.dl_log=self._logbox(f,5)
        if self._dl_q: self._log(self.dl_log,f"📋 {len(self._dl_q)} item(s) restored. Click ▶ Resume.")

    def _dl_fmt_ch(self,_=None):
        fmt=self.dl_fmt.get()
        if any(x in fmt for x in ["mp3","m4a","opus","wav","audio"]):
            self.dl_qual.config(values=["320k","256k","192k","128k","96k"]); self.dl_qual.set("320k")
        elif "images" in fmt:
            self.dl_qual.config(values=["best"]); self.dl_qual.set("best")
        else:
            self.dl_qual.config(values=["1080p","720p","480p","360p","240p","best"]); self.dl_qual.set("720p")

    def _dl_add(self):
        urls=[u.strip() for u in self.dl_urls.get("1.0","end").splitlines() if u.strip()]
        if not urls: return
        fmt=self.dl_fmt.get(); qual=self.dl_qual.get(); save=self.dl_path.get()
        start=self.dl_start.get().strip(); end=self.dl_end.get().strip(); ratio=self.dl_ratio.get()
        existing_urls={i["url"] for i in self._dl_q if i["status"] in ("pending","running","paused")}
        added=dup=0
        for url in urls:
            if url in existing_urls:
                dup+=1; self._log(self.dl_log,f"  ⚠ Already in queue: {url[:60]}")
            else:
                self._dl_q.append({"url":url,"fmt":fmt,"qual":qual,"save":save,
                                    "start":start,"end":end,"ratio":ratio,"status":"pending"})
                existing_urls.add(url); added+=1
        msg=f"➕ Added {added} URL(s)."
        if dup: msg+=f"  ({dup} duplicate(s) skipped)"
        msg+=f"  Queue: {len([i for i in self._dl_q if i['status'] in ('pending','paused')])}"
        self._log(self.dl_log,msg)
        self._dl_stat(); self._save_q(); self._dl_run()

    def _dl_run(self):
        if hasattr(self,"_dl_t") and self._dl_t.is_alive(): return
        self._dl_stop.clear(); self._dl_paused.clear()
        self._dl_t=threading.Thread(target=self._dl_worker,daemon=True); self._dl_t.start()

    def _dl_worker(self):
        pending=[i for i in self._dl_q if i["status"]=="pending"]
        total=len(pending); done=fail=0; self._dl_t0=time.time()
        for idx,item in enumerate(pending):
            if self._dl_stop.is_set(): break
            while self._dl_paused.is_set():
                if self._dl_stop.is_set(): return
                time.sleep(0.3)
            item["status"]="running"; save=item["save"]; fmt=item["fmt"]
            if any(x in fmt for x in ["mp3","m4a","opus","wav","audio"]): save=str(Path(save).parent/"Music")
            elif "images" in fmt: save=str(Path(save).parent/"Images")
            os.makedirs(save,exist_ok=True)
            pct=int(idx/total*100) if total else 0
            self.root.after(0,lambda p=pct:self.dl_bar.config(value=p))
            self.root.after(0,lambda i=idx,t=total,u=item["url"][:55]:self.dl_bar_lbl.set(f"[{i+1}/{t}] {u}..."))
            if self._dl_t0 and idx>0:
                el=time.time()-self._dl_t0
                avg=el/idx; rem=(total-idx)*avg
                eta_s=str(datetime.timedelta(seconds=int(rem)))
                spd=f"{avg:.1f}s/item" if avg<60 else f"{avg/60:.1f}m/item"
                self.root.after(0,lambda e=eta_s,i=idx,t=total,s=spd:
                    self.dl_eta.set(f"ETA {e}  [{i}/{t}]  ~{s}"))
            self._log(self.dl_log,f"\n▶ [{idx+1}/{total}] {item['url']}")
            t0=time.time(); ok=self._dl_item(item,save); el=time.time()-t0
            if ok: done+=1; item["status"]="done"; self._log(self.dl_log,f"  ✔ {el:.1f}s"); self._save_q({"title":"Downloaded","msg":item["url"][:45],"kind":"ok"})
            elif item["status"]=="paused": self._log(self.dl_log,"  ⏸ Paused"); break
            else: fail+=1; item["status"]="failed"; self._save_q({"title":"Failed","msg":item["url"][:45],"kind":"error"})
            self._dl_stat(done,fail)
        self.root.after(0,lambda:self.dl_bar.config(value=0 if self._dl_paused.is_set() else 100))
        self.root.after(0,lambda:self.dl_bar_lbl.set("")); self.root.after(0,lambda:self.dl_eta.set(""))
        if not self._dl_paused.is_set():
            self._log(self.dl_log,f"\n✅ Done — {done} ok, {fail} failed.")
            self.root.after(300,lambda:self.notif.push("Downloads Complete",f"{done} ok, {fail} failed.","ok" if not fail else "warn"))

    def _parse_time(self,t):
        """Convert 2:30 or 0:02:30 to seconds."""
        if not t: return None
        try:
            parts=t.strip().split(":")
            if len(parts)==2: return int(parts[0])*60+float(parts[1])
            if len(parts)==3: return int(parts[0])*3600+int(parts[1])*60+float(parts[2])
            return float(t)
        except: return None

    def _dl_item(self,item,save):
        url=item["url"]; fmt=item["fmt"]; qual=item["qual"]
        start_str=item.get("start",""); end_str=item.get("end",""); ratio=item.get("ratio","original")
        ff_args=self._ff_dir_arg(); ff_exe=self._ff_exe()
        is_audio=any(x in fmt for x in ["mp3","m4a","opus","wav","audio"])
        is_images="images" in fmt
        is_social=any(x in url for x in ["instagram.com","facebook.com","tiktok.com"])
        has_clip=bool(start_str or end_str)

        # P2: Images-only mode
        if is_images:
            return self._dl_images_only(url,save,ff_args,item)

        cmd=["yt-dlp","--no-playlist"]+ff_args
        if is_audio:
            af=next((x for x in ["mp3","m4a","opus","wav"] if x in fmt),"mp3")
            br=qual.replace("k","") if qual.endswith("k") else "320"
            cmd+=["-x","--audio-format",af,"--audio-quality",br,"--embed-thumbnail","--add-metadata"]
        elif is_social: cmd+=["-f","best","--add-header","User-Agent:Mozilla/5.0"]
        elif "mp4" in fmt:
            if qual=="best": cmd+=["-f","bestvideo+bestaudio/best","--merge-output-format","mp4"]
            else: cmd+=["-f",f"bestvideo[height<={qual.replace('p','')}]+bestaudio/best","--merge-output-format","mp4"]
        else: cmd+=["-f","bestvideo+bestaudio/best","--merge-output-format","mp4"]

        # P2: Clip download — use --download-sections or postprocessor
        if has_clip and not is_audio:
            # Parse start/end — support "2:00-2:30" in start field or separate fields
            start_s=None; end_s=None
            if start_str and "-" in start_str and not end_str:
                parts=start_str.split("-",1)
                start_s=self._parse_time(parts[0].strip()); end_s=self._parse_time(parts[1].strip())
            else:
                start_s=self._parse_time(start_str); end_s=self._parse_time(end_str)
            if start_s is not None or end_s is not None:
                # --download-sections is supported in yt-dlp for precise clips
                sec_start=f"{int(start_s//60)}:{int(start_s%60):02d}" if start_s else "0:00"
                sec_end=f"{int(end_s//60)}:{int(end_s%60):02d}" if end_s else ""
                if sec_end: cmd+=["--download-sections",f"*{sec_start}-{sec_end}"]
                elif start_s: cmd+=["--download-sections",f"*{sec_start}-inf"]
                cmd+=["--force-keyframes-at-cuts"]

        # P2: Ratio crop
        if ratio and ratio!="original" and not is_audio:
            ratio_map={"16:9":"16/9","9:16 (vertical)":"9/16","1:1 (square)":"1/1","4:3":"4/3"}
            r_val=ratio_map.get(ratio,"")
            if r_val:
                w,h=r_val.split("/")
                crop_filter=f"crop=min(iw\\,ih*{w}/{h}):min(ih\\,iw*{h}/{w})"
                cmd+=["--ppa",f"Merger+ffmpeg_o:-vf {crop_filter}"]

        cmd+=["--retries","3","--newline","-o",os.path.join(save,"%(title)s.%(ext)s"),"--no-warnings","--progress",url]
        if self._run_tracked(cmd,self.dl_log,item,self._dl_paused,self._dl_stop): return True
        if item["status"]=="paused": return False
        # Fallback
        cmd2=["yt-dlp","--no-playlist","-f","best","--no-check-certificates","--geo-bypass"]+ff_args
        cmd2+=["--add-header","User-Agent:Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)",
               "-o",os.path.join(save,"%(title)s.%(ext)s"),"--no-warnings",url]
        return self._run_tracked(cmd2,self.dl_log,item,self._dl_paused,self._dl_stop)

    def _dl_images_only(self,url,save,ff_args,item):
        """P2: Download images from a post/gallery/profile."""
        cmd=["yt-dlp","--no-playlist"]+ff_args
        cmd+=["-o",os.path.join(save,"%(uploader)s_%(id)s.%(ext)s"),"-f","best[ext=jpg]/best[ext=png]/best[ext=webp]/best","--no-warnings",url]
        if self._run_tracked(cmd,self.dl_log,item,self._dl_paused,self._dl_stop): return True
        # Fallback: --write-thumbnail
        cmd2=["yt-dlp","--no-playlist","--write-thumbnail","--skip-download"]+ff_args
        cmd2+=["-o",os.path.join(save,"%(title)s.%(ext)s"),"--no-warnings",url]
        return self._run_tracked(cmd2,self.dl_log,item,self._dl_paused,self._dl_stop)

    def _run_tracked(self,cmd,box,item,pause_ev,stop_ev):
        try:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  text=True,encoding="utf-8",errors="replace",creationflags=FLAGS)
            for line in proc.stdout:
                l=line.rstrip()
                if not l: continue
                if pause_ev.is_set(): proc.terminate(); item["status"]="paused"; return False
                if stop_ev.is_set(): proc.terminate(); item["status"]="pending"; return False
                if any(k in l.lower() for k in ["[download]","[info]","error","merging"]): self._log(box,f"  {l}")
            proc.wait(); return proc.returncode==0
        except Exception as e: self._log(box,f"  ❌ {e}"); return False

    def _dl_pause(self):
        self._dl_paused.set()
        for i in self._dl_q:
            if i["status"]=="running": i["status"]="paused"
        self._log(self.dl_log,"⏸ Paused."); self._save_q()

    def _dl_resume(self):
        for i in self._dl_q:
            if i["status"] in ("paused","pending"): i["status"]="pending"
        self._dl_paused.clear(); self._dl_stop.clear(); self._log(self.dl_log,"▶ Resuming..."); self._dl_run()

    def _dl_clear(self):
        try:
            # Only clear pending/paused — never touch running or done items
            pending_count = len([i for i in self._dl_q if i["status"] in ("pending","paused")])
            if pending_count == 0:
                self._log(self.dl_log,"ℹ Nothing to clear."); return
            d=AppDialog(self.root,"Clear Queue",
                        f"Remove {pending_count} pending item(s)? (running/done kept)",
                        ("Cancel","Clear"),"🗑")
            if d.wait()=="Clear":
                self._dl_q=[i for i in self._dl_q if i["status"] not in ("pending","paused")]
                self._dl_stat(); self._save_q()
                self._log(self.dl_log,"🗑 Pending items cleared.")
        except Exception as e:
            try: self._log(self.dl_log,f"⚠ Clear: {e}")
            except: pass

    def _dl_stat(self,done=None,fail=None):
        p=len([i for i in self._dl_q if i["status"] in ("pending","running","paused")])
        d=done if done is not None else len([i for i in self._dl_q if i["status"]=="done"])
        fl=fail if fail is not None else len([i for i in self._dl_q if i["status"]=="failed"])
        self.root.after(0,lambda:self.dl_stats.set(f"Queue: {p}  |  Done: {d}  |  Failed: {fl}"))

    # ── TAB 2: MUSIC — P3 ─────────────────────────────────
    def _tab_music(self,nb):
        f=tk.Frame(nb,bg=T["bg3"]); nb.add(f,text="  🎵 Music  ")
        self._sec(f,"YouTube Music Downloader","Songs · Playlists · Synced lyrics · Original song title")
        info=tk.Frame(f,bg=T["bg4"],pady=8); info.pack(fill="x",padx=22,pady=(0,10))
        tk.Label(info,text='  Paste a YouTube Music URL, Spotify URL, or song name like  "Artist - Song Title"',
                 font=self._F(9),fg=T["cyan"],bg=T["bg4"],anchor="w").pack(fill="x",padx=6)
        tk.Label(info,text='  For playlists: paste the full YouTube Music playlist URL.',
                 font=self._F(9),fg=T["muted"],bg=T["bg4"],anchor="w").pack(fill="x",padx=6)
        self._lbl(f,"URL(s) or song name(s) — one per line:")
        self.mu_urls=self._textbox(f,4)
        row=tk.Frame(f,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=(4,0))
        self._lbl(row,"Format:","left")
        self.mu_fmt=ttk.Combobox(row,values=["mp3","m4a","flac","ogg","opus"],width=10,state="readonly")
        self.mu_fmt.set("mp3"); self.mu_fmt.pack(side="left",padx=(4,20))
        self._lbl(row,"Source:","left")
        self.mu_src=ttk.Combobox(row,values=["youtube-music","youtube","youtube-music youtube"],width=22,state="readonly")
        self.mu_src.set("youtube-music"); self.mu_src.pack(side="left",padx=(4,0))
        row2=tk.Frame(f,bg=T["bg3"]); row2.pack(fill="x",padx=22,pady=(6,0))
        self.mu_lyrics=tk.BooleanVar(value=True)
        self.mu_poster=tk.BooleanVar(value=True)
        self.mu_meta  =tk.BooleanVar(value=True)
        for var,lbl in [(self.mu_lyrics,"Embed synced lyrics (Apple Music compatible)"),
                        (self.mu_poster,"Embed album art (1:1 square, no separate file)"),
                        (self.mu_meta,"Embed metadata (artist / album / year)")]:
            tk.Checkbutton(row2,variable=var,text=lbl,font=self._F(9),
                           fg=T["text"],bg=T["bg3"],selectcolor=T["bg4"],activebackground=T["bg3"]).pack(side="left",padx=(0,16))
        fr=tk.Frame(f,bg=T["bg3"]); fr.pack(fill="x",padx=22,pady=(8,0))
        self._lbl(fr,"Save to:","left")
        self.mu_path=self._enil(fr,self.cfg["dl_path"]+"/Music")
        self._btn(fr,"📁",lambda:self._browse_dir(self.mu_path),sm=True,side="left")
        self._btn(fr,"📂",lambda:self._open_f(self.mu_path.get()),sm=True,side="left")
        brow=tk.Frame(f,bg=T["bg3"]); brow.pack(fill="x",padx=22,pady=(8,2))
        self._btn(brow,"⬇  Add & Download",self._mu_add,side="left",color=T["acc"])
        self._btn(brow,"⏸",self._mu_pause,sm=True,side="left",color=T["yellow"])
        self._btn(brow,"▶ Resume",self._mu_resume,sm=True,side="left",color=T["cyan"])
        self._btn(brow,"🗑",self._mu_clear,sm=True,side="left",color=T["red"])
        self.mu_stats=tk.StringVar(value="Queue: 0  |  Downloaded: 0  |  Failed: 0")
        tk.Label(f,textvariable=self.mu_stats,font=self._F(9),fg=T["acc"],bg=T["bg3"]).pack(anchor="w",padx=22,pady=(4,0))
        self.mu_bar=self._mkbar(f); self.mu_bar_lbl=tk.StringVar(value="")
        tk.Label(f,textvariable=self.mu_bar_lbl,font=self._F(8),fg=T["muted"],bg=T["bg3"]).pack(anchor="w",padx=22)
        self._lbl(f,"Log:"); self.mu_log=self._logbox(f,7)
        if self._mu_q: self._log(self.mu_log,f"📋 {len(self._mu_q)} track(s) restored. Click ▶ Resume.")

    def _mu_add(self):
        qs=[u.strip() for u in self.mu_urls.get("1.0","end").splitlines() if u.strip()]
        if not qs: return
        save=self.mu_path.get(); fmt=self.mu_fmt.get(); src=self.mu_src.get()
        poster = self.mu_poster.get() if hasattr(self,"mu_poster") else True
        for q in qs:
            self._mu_q.append({"query":q,"save":save,"fmt":fmt,"src":src,
                                "lyrics":self.mu_lyrics.get(),"poster":poster,
                                "meta":self.mu_meta.get(),"status":"pending"})
        self._log(self.mu_log,f"➕ Added {len(qs)} item(s). Queue: {len(self._mu_q)}")
        self._mu_stat(); self._save_q(); self._mu_run()

    def _mu_run(self):
        if hasattr(self,"_mu_t") and self._mu_t.is_alive(): return
        self._mu_stop.clear(); self._mu_paused.clear()
        self._mu_t=threading.Thread(target=self._mu_worker,daemon=True); self._mu_t.start()

    def _mu_worker(self):
        pending=[i for i in self._mu_q if i["status"]=="pending"]
        total=len(pending); ok=fail=0
        for idx,item in enumerate(pending):
            if self._mu_stop.is_set(): break
            while self._mu_paused.is_set():
                if self._mu_stop.is_set(): return
                time.sleep(0.3)
            item["status"]="running"
            pct=int(idx/total*100) if total else 0
            self.root.after(0,lambda p=pct:self.mu_bar.config(value=p))
            self.root.after(0,lambda i=idx,t=total:self.mu_bar_lbl.set(f"[{i+1}/{t}] {item['query'][:50]}..."))
            self._log(self.mu_log,f"\n[{idx+1}/{total}] {item['query']}")
            t0=time.time(); success=self._mu_dl(item); el=time.time()-t0
            if success: ok+=1; item["status"]="done"; self._log(self.mu_log,f"  ✔ {el:.1f}s"); self._save_q({"title":"Music Downloaded","msg":item["query"][:45],"kind":"ok"})
            elif item["status"]=="paused": self._log(self.mu_log,"  ⏸ Paused"); break
            else: fail+=1; item["status"]="failed"
            self._mu_stat(ok,fail)
        self.root.after(0,lambda:self.mu_bar.config(value=0 if self._mu_paused.is_set() else 100))
        self.root.after(0,lambda:self.mu_bar_lbl.set(""))
        if not self._mu_paused.is_set():
            self._log(self.mu_log,f"\n✅ Done — {ok} downloaded, {fail} failed.")
            self.root.after(300,lambda:self.notif.push("Music Done",f"{ok} downloaded, {fail} failed.","ok" if not fail else "warn"))

    def _mu_dl(self,item):
        """
        P3: Download music WITHOUT album art.
        - Original title preserved (%(title)s — yt-dlp keeps original)
        - Lyrics downloaded from internet and embedded
        - Artist + album metadata embedded
        - Spotdl for Spotify URLs (correct v4: subcommand + URL + options after)
        """
        query=item["query"]; save=item["save"]; fmt=item["fmt"]
        src=item["src"]; embed_lyrics=item.get("lyrics",True); embed_meta=item.get("meta",True)
        ff_args=self._ff_dir_arg(); os.makedirs(save,exist_ok=True)

        if "open.spotify.com" in query:
            return self._mu_spotdl(query,save,fmt,item)

        is_url=query.startswith("http")
        is_playlist=is_url and ("playlist" in query or "list=" in query)
        src_map={"youtube-music":"ytmsearch","youtube":"ytsearch","youtube-music youtube":"ytmsearch"}
        prefix=src_map.get(src,"ytmsearch")
        search_arg=f"{prefix}:{query}" if not is_url else query

        cmd=["yt-dlp"]
        if not is_playlist: cmd+=["--no-playlist"]
        cmd+=ff_args

        # Audio extraction — keep quality max
        cmd+=["-x","--audio-format",fmt,"--audio-quality","0"]

        # Album art: embed 1:1 square thumbnail only if requested
        embed_poster = item.get("poster", True)
        if embed_poster:
            cmd+=["--embed-thumbnail","--convert-thumbnails","jpg"]
            # Crop to 1:1 square — no separate image file, embedded only
            cmd+=["--ppa","EmbedThumbnail+ffmpeg_o:-vf crop=min(iw\\,ih):min(iw\\,ih),setsar=1"]

        # Full metadata: title (original), artist, album, year, track
        if embed_meta:
            cmd+=["--add-metadata"]

        # Lyrics: .lrc sidecar file Apple Music reads automatically
        # Also try to get synced lyrics (timestamped)
        if embed_lyrics:
            cmd+=["--write-subs","--write-auto-subs",
                  "--sub-langs","en.*",
                  "--convert-subs","lrc",
                  "--embed-subs"]  # embed in m4a/flac; ignored for mp3 (use .lrc file)

        # Original title — yt-dlp %(title)s is always the original
        cmd+=["--retries","3","--newline",
              "-o",os.path.join(save,"%(title)s.%(ext)s"),
              "--no-warnings","--progress",search_arg]

        self._log(self.mu_log,f"  ⚙ Downloading {fmt} + lyrics...")
        try:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  text=True,encoding="utf-8",errors="replace",creationflags=FLAGS)
            for line in proc.stdout:
                l=line.rstrip()
                if not l: continue
                if self._mu_paused.is_set(): proc.terminate(); item["status"]="paused"; return False
                if self._mu_stop.is_set(): proc.terminate(); item["status"]="pending"; return False
                if any(k in l.lower() for k in ["[download]","[info]","error","embedding","merging","writing","subtitle"]): self._log(self.mu_log,f"  {l}")
            proc.wait()
            if proc.returncode==0:
                self._fix_lrc(save); return True
            # Retry without lyrics flags
            self._log(self.mu_log,"  ↩ Retrying without lyrics...")
            cmd2=["yt-dlp"]
            if not is_playlist: cmd2+=["--no-playlist"]
            cmd2+=ff_args+["-x","--audio-format",fmt,"--audio-quality","0"]
            if embed_meta: cmd2+=["--add-metadata"]
            cmd2+=["--retries","3","--newline",
                   "-o",os.path.join(save,"%(title)s.%(ext)s"),
                   "--no-warnings","--progress",search_arg]
            proc2=subprocess.Popen(cmd2,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                   text=True,encoding="utf-8",errors="replace",creationflags=FLAGS)
            for line in proc2.stdout:
                l=line.rstrip()
                if not l: continue
                if self._mu_paused.is_set(): proc2.terminate(); item["status"]="paused"; return False
                if self._mu_stop.is_set(): proc2.terminate(); item["status"]="pending"; return False
            proc2.wait()
            if proc2.returncode==0: return True
            self._log(self.mu_log,"  ↩ Trying spotdl...")
            return self._mu_spotdl(query,save,fmt,item)
        except FileNotFoundError:
            self._log(self.mu_log,"  ❌ yt-dlp not found. Re-run setup."); return False
        except Exception as e:
            self._log(self.mu_log,f"  ❌ {e}"); return False

    def _fix_lrc(self,save):
        """Ensure .lrc files have UTF-8 BOM for Apple Music compatibility."""
        try:
            for lrc in Path(save).glob("*.lrc"):
                c=lrc.read_text("utf-8",errors="ignore")
                if c.strip() and not c.startswith("\ufeff"):
                    lrc.write_bytes(("\ufeff"+c).encode("utf-8"))
        except: pass

    def _mu_spotdl(self,query,save,fmt,item):
        """Correct spotdl v4: download + URL + options AFTER subcommand."""
        ff=self._ff_exe()
        cmd=[sys.executable,"-m","spotdl","download",query,
             "--output",os.path.join(save,"{title}.{output-ext}"),  # P3: original title
             "--format",fmt,"--ffmpeg",ff,"--print-errors"]
        self._log(self.mu_log,f"  ⚙ spotdl {fmt}...")
        try:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  text=True,encoding="utf-8",errors="replace",creationflags=FLAGS,cwd=save)
            lines=[]
            for line in proc.stdout:
                l=line.rstrip()
                if not l: continue
                if self._mu_paused.is_set(): proc.terminate(); item["status"]="paused"; return False
                if self._mu_stop.is_set(): proc.terminate(); item["status"]="pending"; return False
                lines.append(l)
                if any(k in l.lower() for k in ["downloaded","error","found","processing"]): self._log(self.mu_log,f"  {l}")
            proc.wait(); combined="\n".join(lines)
            return proc.returncode==0 or "Downloaded" in combined
        except FileNotFoundError: self._log(self.mu_log,"  ❌ spotdl not found."); return False
        except Exception as e: self._log(self.mu_log,f"  ❌ {e}"); return False

    def _mu_pause(self):
        self._mu_paused.set()
        for i in self._mu_q:
            if i["status"]=="running": i["status"]="paused"
        self._log(self.mu_log,"⏸ Paused."); self._save_q()

    def _mu_resume(self):
        for i in self._mu_q:
            if i["status"] in ("paused","pending"): i["status"]="pending"
        self._mu_paused.clear(); self._mu_stop.clear(); self._log(self.mu_log,"▶ Resuming..."); self._mu_run()

    def _mu_clear(self):
        d=AppDialog(self.root,"Clear","Remove pending music?",("Cancel","Clear"),"🗑")
        if d.wait()=="Clear":
            self._mu_q=[i for i in self._mu_q if i["status"]=="done"]; self._mu_stat(); self._save_q()

    def _mu_stat(self,done=None,fail=None):
        p=len([i for i in self._mu_q if i["status"] in ("pending","running","paused")])
        d=done if done is not None else len([i for i in self._mu_q if i["status"]=="done"])
        fl=fail if fail is not None else len([i for i in self._mu_q if i["status"]=="failed"])
        self.root.after(0,lambda:self.mu_stats.set(f"Queue: {p}  |  Downloaded: {d}  |  Failed: {fl}"))

    # ── TAB 3: SCRAPER — P4 ──────────────────────────────
    def _tab_scraper(self,nb):
        f=tk.Frame(nb,bg=T["bg3"]); nb.add(f,text="  🕷 Scraper  ")
        self._sec(f,"Video & Post Link Scraper","YouTube · Instagram (all posts) · Facebook (all posts) · TikTok · Reddit · Twitter · Adult sites")
        row=tk.Frame(f,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=(0,6))
        self._lbl(row,"Platform:","left")
        self.sc_mode=ttk.Combobox(row,values=[
            "YouTube Channel/Playlist","Instagram Profile (all posts)","Facebook Page (all posts)",
            "TikTok User","Reddit User/Subreddit","Twitter/X User",
            "Adult site channel (Pornhub/xHamster/xnxx/RedTube etc.)",
        ],width=42,state="readonly")
        self.sc_mode.set("YouTube Channel/Playlist"); self.sc_mode.pack(side="left",padx=(4,0))
        self._lbl(f,"URL or @username:"); self.sc_inp=self._entry(f,"https://...")
        row2=tk.Frame(f,bg=T["bg3"]); row2.pack(fill="x",padx=22,pady=(4,0))
        self._lbl(row2,"Max:","left")
        self.sc_lim=ttk.Combobox(row2,values=["25","50","100","200","500","all"],width=8,state="readonly")
        self.sc_lim.set("100"); self.sc_lim.pack(side="left",padx=(4,20))
        fr=tk.Frame(f,bg=T["bg3"]); fr.pack(fill="x",padx=22,pady=(4,0))
        self._lbl(fr,"Save .txt folder:","left")
        self.sc_save=self._enil(fr,self.cfg["dl_path"]); self._btn(fr,"📁",lambda:self._browse_dir(self.sc_save),sm=True,side="left")
        brow=tk.Frame(f,bg=T["bg3"]); brow.pack(fill="x",padx=22,pady=(8,0))
        self._btn(brow,"🕷  Scrape",self._do_scrape,side="left",color=T["acc"])
        self._btn(brow,"Copy",self._copy_sc,sm=True,side="left")
        self._btn(brow,"Save .txt",self._save_sc,sm=True,side="left")
        self._btn(brow,"→ Downloader",self._sc_to_dl,sm=True,side="left",color=T["cyan"])
        self.sc_bar=self._mkbar(f); self.sc_bar.config(value=0)
        self.sc_count=tk.StringVar(value="")
        tk.Label(f,textvariable=self.sc_count,font=self._F(9),fg=T["acc"],bg=T["bg3"]).pack(anchor="w",padx=22)
        self._lbl(f,"Scraped Links:"); self.sc_log=self._logbox(f)

    def _do_scrape(self):
        mode=self.sc_mode.get(); inp=self.sc_inp.get().strip()
        if not inp: return
        lim=None if self.sc_lim.get()=="all" else int(self.sc_lim.get())
        self.sc_bar.config(mode="indeterminate"); self.sc_bar.start(10)
        self._scraped=[]; self.sc_count.set("Scraping...")
        self._log(self.sc_log,f"🕷 {mode}...")
        def run():
            try:
                links=self._scrape_links(mode,inp,lim)
                self._scraped=links
                name=inp.strip().lstrip("@")
                for pat in [r'@([a-zA-Z0-9_.]+)',r'/([a-zA-Z0-9_.]+)/?$']:
                    m=re.search(pat,name)
                    if m: name=m.group(1); break
                name=re.sub(r'[^a-zA-Z0-9_\-]','_',name)[:40] or "scraped"
                self._sc_name=name
                self.root.after(0,lambda:self.sc_count.set(f"✅ Found {len(links)} links"))
                self._log(self.sc_log,f"✅ {len(links)} links:")
                for l in links: self._log(self.sc_log,l)
                self.root.after(200,lambda:self.notif.push("Scrape Done",f"{len(links)} links","ok"))
            except Exception as e:
                self._log(self.sc_log,f"❌ {e}"); self.root.after(0,lambda:self.sc_count.set(f"❌ Error"))
            self.root.after(0,lambda:(self.sc_bar.stop(),self.sc_bar.config(mode="determinate",value=100)))
        threading.Thread(target=run,daemon=True).start()

    def _scrape_links(self,mode,inp,lim):
        if "YouTube" in mode: return self._yt_flat(inp,lim)
        if "Instagram" in mode: return self._ig_posts(inp,lim)
        if "Facebook" in mode: return self._fb_posts(inp,lim)
        if "TikTok" in mode:
            u=inp.lstrip("@"); url=inp if inp.startswith("http") else f"https://www.tiktok.com/@{u}"
            return self._yt_flat(url,lim)
        if "Reddit" in mode:
            u=inp.lstrip("r/").lstrip("u/").lstrip("/"); url=inp if inp.startswith("http") else f"https://www.reddit.com/r/{u}"
            return self._yt_flat(url,lim)
        if "Twitter" in mode:
            u=inp.lstrip("@"); url=inp if inp.startswith("http") else f"https://twitter.com/{u}/media"
            return self._yt_flat(url,lim)
        if "Adult" in mode:
            url=inp if inp.startswith("http") else f"https://{inp}"; return self._yt_flat_adult(url,lim)
        return self._yt_flat(inp,lim)

    def _yt_flat(self,url,lim):
        cmd=["yt-dlp","--flat-playlist","--print","url","--no-warnings","--yes-playlist",url]
        if lim: cmd+=["--playlist-end",str(lim)]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=180,creationflags=FLAGS)
        links=[l.strip() for l in r.stdout.splitlines() if l.strip()]
        if not links:
            cmd2=["yt-dlp","--flat-playlist","--print","webpage_url","--no-warnings",url]
            if lim: cmd2+=["--playlist-end",str(lim)]
            r2=subprocess.run(cmd2,capture_output=True,text=True,timeout=180,creationflags=FLAGS)
            links=[l.strip() for l in r2.stdout.splitlines() if l.strip()]
        return links

    def _yt_flat_adult(self,url,lim):
        links=self._yt_flat(url,lim)
        if links: return links
        for extra in [["--no-check-certificates","--add-header","User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64)"],
                      ["--extract-flat","in_playlist","--no-check-certificates"]]:
            cmd=["yt-dlp","--flat-playlist","--print","url","--no-warnings","--yes-playlist"]+extra+[url]
            if lim: cmd+=["--playlist-end",str(lim)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=180,creationflags=FLAGS)
            links=[l.strip() for l in r.stdout.splitlines() if l.strip()]
            if links: return links
        return []

    def _ig_posts(self,inp,lim):
        """P4: Instagram — multiple methods, robust fallback."""
        username=inp.strip().lstrip("@")
        if "instagram.com/" in username: username=re.sub(r".*/([^/?#]+).*",r"\1",username).strip("/")
        self._log(self.sc_log,f"  Method 1: yt-dlp for @{username}...")
        # Method 1: yt-dlp
        try:
            for attempt_url in [f"https://www.instagram.com/{username}/",
                                 f"https://www.instagram.com/{username}/posts/"]:
                cmd=["yt-dlp","--flat-playlist","--print","webpage_url","--no-warnings","--yes-playlist",
                     "--add-header","User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64)",attempt_url]
                if lim: cmd+=["--playlist-end",str(lim)]
                r=subprocess.run(cmd,capture_output=True,text=True,timeout=60,creationflags=FLAGS)
                links=[l.strip() for l in r.stdout.splitlines() if l.strip() and "instagram.com" in l]
                if links: self._log(self.sc_log,f"  ✔ yt-dlp: {len(links)} links"); return links
        except Exception as e: self._log(self.sc_log,f"  yt-dlp: {e}")
        # Method 2: instaloader (anonymous — works for public)
        self._log(self.sc_log,f"  Method 2: instaloader for @{username}...")
        try:
            import instaloader
            L=self._ig_loader
            if L is None:
                L=instaloader.Instaloader(sleep=False,quiet=True,download_pictures=False,
                                          download_videos=False,download_video_thumbnails=False,
                                          download_geotags=False,download_comments=False,save_metadata=False)
            profile=instaloader.Profile.from_username(L.context,username)
            links=[f"https://www.instagram.com/p/{p.shortcode}/" for p in
                   (list(profile.get_posts())[:lim] if lim else profile.get_posts())]
            if links: self._log(self.sc_log,f"  ✔ instaloader: {len(links)} links"); return links
        except Exception as e:
            raise RuntimeError(f"Instagram @{username} failed.\nTip: Log in via Images tab for private profiles.\nError: {e}")

    def _fb_posts(self,inp,lim):
        """P4: Facebook — multiple methods."""
        url=inp if inp.startswith("http") else f"https://www.facebook.com/{urllib.parse.quote(inp.lstrip('@'),safe='')}"
        self._log(self.sc_log,f"  Method 1: yt-dlp for {url}...")
        # Method 1: yt-dlp (works for public pages)
        for fb_url in [url, url+"/posts", url+"/videos"]:
            try:
                cmd=["yt-dlp","--flat-playlist","--print","webpage_url","--no-warnings","--yes-playlist",
                     "--add-header","User-Agent:Mozilla/5.0",fb_url]
                if lim: cmd+=["--playlist-end",str(lim)]
                r=subprocess.run(cmd,capture_output=True,text=True,timeout=60,creationflags=FLAGS)
                links=[l.strip() for l in r.stdout.splitlines() if l.strip() and "facebook.com" in l]
                if links: self._log(self.sc_log,f"  ✔ yt-dlp: {len(links)} links"); return links
            except Exception as e: self._log(self.sc_log,f"  yt-dlp {fb_url}: {e}")
        # Method 2: generic flat scrape
        try:
            links=self._yt_flat(url,lim)
            if links: return links
        except: pass
        raise RuntimeError(f"Could not scrape Facebook: {url}\nFacebook blocks most automated scraping of private/authenticated content.")

    def _copy_sc(self):
        if not self._scraped: return
        self.root.clipboard_clear(); self.root.clipboard_append("\n".join(self._scraped))
        self.notif.push("Copied",f"{len(self._scraped)} links","ok")

    def _save_sc(self):
        if not self._scraped: return
        name=getattr(self,"_sc_name","scraped"); d=self.sc_save.get() or self.cfg["dl_path"]
        folder=os.path.join(d,name); os.makedirs(folder,exist_ok=True)
        ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out=os.path.join(folder,f"{name}_{ts}.txt")
        Path(out).write_text("\n".join(self._scraped),"utf-8")
        self.notif.push("Saved",out,"ok"); self._log(self.sc_log,f"✔ Saved: {out}")

    def _sc_to_dl(self):
        if not self._scraped: return
        self.dl_urls.delete("1.0","end"); self.dl_urls.insert("1.0","\n".join(self._scraped))
        self.notif.push("Sent",f"{len(self._scraped)} links → Downloader","info")

    # ── TAB 4: ECOMMERCE — P5 ────────────────────────────
    def _tab_ecomm(self,nb):
        f=tk.Frame(nb,bg=T["bg3"]); nb.add(f,text="  🛒 Ecommerce  ")
        self._sec(f,"E-commerce Product Scraper","AliExpress · Alibaba · Ramsha · Laam · Amazon · eBay · Daraz · any store")
        self._lbl(f,"Store / Category URL:")
        self.ec_url=self._entry(f,"https://...")
        row=tk.Frame(f,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=(4,0))
        self._lbl(row,"Max products:","left")
        self.ec_lim=ttk.Combobox(row,values=["25","50","100","200","all"],width=8,state="readonly")
        self.ec_lim.set("50"); self.ec_lim.pack(side="left",padx=(4,20))
        self.ec_dl_media=tk.BooleanVar(value=False)
        tk.Checkbutton(row,text="Download product images & videos",variable=self.ec_dl_media,
                       font=self._F(9),fg=T["text"],bg=T["bg3"],selectcolor=T["bg4"],activebackground=T["bg3"]).pack(side="left")
        fr=tk.Frame(f,bg=T["bg3"]); fr.pack(fill="x",padx=22,pady=(8,0))
        self._lbl(fr,"Base save folder:","left")
        self.ec_save=self._enil(fr,self.cfg["dl_path"]+"/Ecommerce")
        self._btn(fr,"📁",lambda:self._browse_dir(self.ec_save),sm=True,side="left")
        self._btn(fr,"📂",lambda:self._open_f(getattr(self,"_ec_folder",self.ec_save.get())),sm=True,side="left")
        brow=tk.Frame(f,bg=T["bg3"]); brow.pack(fill="x",padx=22,pady=(8,2))
        self._btn(brow,"🕷  Scrape Products",self._do_ec,side="left",color=T["acc"])
        self._btn(brow,"Save CSV",self._ec_csv,sm=True,side="left",color=T["cyan"])
        self.ec_bar=self._mkbar(f); self.ec_bar.config(value=0)
        self.ec_stats=tk.StringVar(value="")
        tk.Label(f,textvariable=self.ec_stats,font=self._F(9),fg=T["acc"],bg=T["bg3"]).pack(anchor="w",padx=22)
        self._lbl(f,"Results:"); self.ec_log=self._logbox(f,10); self._ec_prods=[]

    def _do_ec(self):
        url=self.ec_url.get().strip()
        if not url: return
        lim=None if self.ec_lim.get()=="all" else int(self.ec_lim.get())
        dl_media=self.ec_dl_media.get()
        parts=[p for p in url.split("/") if p and "." not in p and p not in ("http:","https:","www","en","products","search","category","collections","shop")]
        brand=parts[-1] if parts else "store"
        brand=re.sub(r'[^a-zA-Z0-9_\-]','_',brand)[:40] or "store"
        base=self.ec_save.get(); brand_folder=os.path.join(base,brand); os.makedirs(brand_folder,exist_ok=True)
        self._ec_folder=brand_folder; self._ec_brand=brand
        self.ec_bar.config(mode="indeterminate"); self.ec_bar.start(10)
        self._ec_prods=[]; self.ec_stats.set(f"Scraping {url}...")
        def run():
            try:
                from bs4 import BeautifulSoup
                prods=self._scrape_products(url,lim,brand_folder,dl_media)
                self._ec_prods=prods
                self.root.after(0,lambda:self.ec_stats.set(f"✅ {len(prods)} products — folder: {brand}"))
                for i,p in enumerate(prods[:20],1):
                    self._log(self.ec_log,f"\n#{i:03d}  [{p.get('category','N/A')}]  {p.get('title','N/A')[:55]}")
                    self._log(self.ec_log,f"      Price: {p.get('price','N/A')}  Sale: {p.get('sale_price','N/A')}")
                    self._log(self.ec_log,f"      Desc: {p.get('description','')[:60]}")
                    self._log(self.ec_log,f"      {p.get('url','')[:70]}")
                if len(prods)>20: self._log(self.ec_log,f"\n  ... +{len(prods)-20} more")
                self.notif.push("Scraped",f"{len(prods)} products from {brand}","ok")
            except ImportError: self._log(self.ec_log,"❌ beautifulsoup4 not installed. Settings → Re-run Setup.")
            except Exception as e: self._log(self.ec_log,f"❌ {e}"); self.notif.push("Error",str(e)[:50],"error")
            self.root.after(0,lambda:(self.ec_bar.stop(),self.ec_bar.config(mode="determinate",value=100)))
        threading.Thread(target=run,daemon=True).start()

    def _scrape_products(self,url,lim,brand_folder,dl_media):
        """P5: Comprehensive product scraper — price, sale price, description all extracted."""
        from bs4 import BeautifulSoup
        import urllib.request as ur, json as _j
        hdrs={
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept":"text/html,application/xhtml+xml,*/*;q=0.9","Accept-Language":"en-US,en;q=0.9",
            "Accept-Encoding":"gzip, deflate, br","Connection":"keep-alive",
        }
        # Try requests library first (handles gzip/br encoding better)
        html = None
        try:
            import requests as _req
            _r = _req.get(url, headers=hdrs, timeout=20, allow_redirects=True)
            _r.encoding = _r.apparent_encoding
            html = _r.text
        except Exception:
            pass
        if not html:
            req=ur.Request(url,headers=hdrs)
            with ur.urlopen(req,timeout=25) as r: html=r.read().decode("utf-8",errors="ignore")
        soup=BeautifulSoup(html,"lxml"); products=[]

        # Strategy 1: JSON-LD
        for script in soup.find_all("script",{"type":"application/ld+json"}):
            try:
                data=_j.loads(script.string or "")
                items=data if isinstance(data,list) else [data]
                for it in items:
                    if it.get("@type") in ("Product","ItemPage"):
                        offers=it.get("offers",{}); imgs=it.get("image",[])
                        if isinstance(imgs,str): imgs=[imgs]
                        elif isinstance(imgs,dict): imgs=[imgs.get("url","")]
                        # Price extraction
                        price="N/A"; sale_price="N/A"
                        if isinstance(offers,dict):
                            p_val=offers.get("price",""); curr=offers.get("priceCurrency","")
                            price=f"{curr} {p_val}".strip() if curr else str(p_val) if p_val else "N/A"
                            low=offers.get("lowPrice",""); high=offers.get("highPrice","")
                            if low and high and low!=high: sale_price=f"{curr} {low}".strip() if curr else str(low)
                        elif isinstance(offers,list) and offers:
                            prices_list=[str(o.get("price","")) for o in offers if o.get("price")]
                            if prices_list:
                                price=prices_list[0]
                                if len(prices_list)>1: sale_price=min(prices_list,key=lambda x:float(re.sub(r'[^\d.]','',x) or '0'))
                        desc=it.get("description","") or ""
                        brand_name=it.get("brand",{}).get("name","N/A") if isinstance(it.get("brand"),dict) else it.get("brand","N/A")
                        products.append({
                            "product_no":len(products)+1,"category":it.get("category",brand_name),
                            "title":it.get("name","N/A"),"price":price,"sale_price":sale_price,
                            "url":it.get("url",url),"images":len([i for i in imgs if i]),
                            "videos":0,"description":desc[:150],
                        })
            except: pass

        # Strategy 2: Open Graph for single product page
        if not products:
            og_title=soup.find("meta",property="og:title")
            if og_title:
                # Try multiple price selectors
                price_el=None
                for sel in [
                    {"itemprop":"price"},{"class":re.compile(r"price",re.I)},
                    {"id":re.compile(r"price",re.I)},{"class":re.compile(r"amount",re.I)},
                ]:
                    price_el=soup.find(["span","div","p","strong"],attrs=sel)
                    if price_el and price_el.get_text(strip=True): break
                sale_el=None
                for sel in [{"class":re.compile(r"sale|discount|special",re.I)},{"class":re.compile(r"old.*price|price.*old",re.I)}]:
                    sale_el=soup.find(["span","div"],attrs=sel)
                    if sale_el and sale_el.get_text(strip=True): break
                desc_el=soup.find("meta",property="og:description") or soup.find({"itemprop":"description"}) or soup.find(class_=re.compile(r"desc|detail",re.I))
                desc=desc_el.get("content","") or (desc_el.get_text(strip=True) if desc_el else "") if desc_el else ""
                imgs=soup.find_all("meta",property="og:image")
                products.append({
                    "product_no":1,"category":"N/A",
                    "title":og_title.get("content","N/A"),
                    "price":price_el.get_text(strip=True) if price_el else "N/A",
                    "sale_price":sale_el.get_text(strip=True) if sale_el else "N/A",
                    "url":url,"images":len(imgs),"videos":0,
                    "description":desc[:150],
                })

        # Strategy 3: CSS heuristics for listing pages
        if not products:
            sel_groups=[
                [("div",["product-item","item-node","sku-item","goods-item","search-item","product-card","item-card","product-listing"]),
                 ("li",["product","item","product-node","grid-item","search-item"]),
                 ("article",["product","item","card","product-card"]),
                 ("div",["col-","grid-item","product","card-product"])],
            ]
            for selectors in sel_groups:
                for tag,hints in selectors:
                    cards=soup.find_all(tag,class_=lambda c,h=hints:c and any(x in str(c).lower() for x in h))
                    if len(cards)<2: continue
                    for i,card in enumerate(cards[:lim or 200]):
                        # Title
                        title="N/A"
                        for t_sel in [{"class":re.compile(r"title|name|product.?name",re.I)},
                                      {"itemprop":"name"}]:
                            tel=card.find(["h1","h2","h3","h4","a","span","div"],attrs=t_sel)
                            if tel and len(tel.get_text(strip=True))>3: title=tel.get_text(strip=True)[:80]; break
                        if title=="N/A":
                            for t in ["h2","h3","h4"]:
                                tel=card.find(t)
                                if tel and len(tel.get_text(strip=True))>3: title=tel.get_text(strip=True)[:80]; break
                        if len(title)<3: continue

                        # P5: Price — try multiple selectors, get all price-like values
                        price_texts=[]
                        for p_sel in [{"class":re.compile(r"price|cost|amount",re.I)},{"itemprop":"price"}]:
                            for pel in card.find_all(attrs=p_sel):
                                pt=pel.get_text(strip=True)
                                if pt and re.search(r'[\d]',pt) and len(pt)<25: price_texts.append(pt)
                        # Also look for data-price attributes
                        for el in card.find_all(attrs={"data-price":True}):
                            price_texts.append(str(el.get("data-price","")))
                        price=price_texts[0] if price_texts else "N/A"
                        # Sale price: second price or one with "sale" class
                        sale_price="N/A"
                        sale_el=card.find(class_=re.compile(r"sale|discount|special|was|old|strike|through|original",re.I))
                        if sale_el and re.search(r'[\d]',sale_el.get_text()):
                            sale_price=sale_el.get_text(strip=True)[:25]
                        elif len(price_texts)>1:
                            # Pick the lower of two prices as sale price
                            def _num(s):
                                try: return float(re.sub(r'[^\d.]','',s) or '999999')
                                except: return 999999
                            sale_price=min(price_texts[:2],key=_num) if len(price_texts)>=2 else price_texts[1]

                        # P5: Description
                        desc=""
                        for d_sel in [{"class":re.compile(r"desc|detail|brief|summary",re.I)},{"itemprop":"description"}]:
                            del_el=card.find(attrs=d_sel)
                            if del_el: desc=del_el.get_text(strip=True)[:150]; break

                        # Category
                        cat="N/A"
                        for c_sel in [{"class":re.compile(r"categ|breadcrumb|tag|label",re.I)},{"itemprop":"category"}]:
                            cat_el=card.find(attrs=c_sel)
                            if cat_el: cat=cat_el.get_text(strip=True)[:50]; break

                        # URL
                        link_el=card.find("a",href=True)
                        purl=link_el["href"] if link_el else url
                        if purl.startswith("//"): purl="https:"+purl
                        elif purl.startswith("/"): purl=urllib.parse.urljoin(url,purl)
                        imgs=card.find_all("img"); vids=card.find_all(["video","source"])
                        products.append({
                            "product_no":i+1,"category":cat,"title":title,
                            "price":price,"sale_price":sale_price,"url":purl,
                            "images":len(imgs),"videos":len(vids),"description":desc,
                        })
                    if products: break
                if products: break

        if lim: products=products[:lim]

        # Download media — folder named after product title
        if dl_media and products:
            self._log(self.ec_log,"📥 Downloading product images...")
            hdrs2={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"image/*,*/*;q=0.8","Referer":url}
            for p in products:
                safe_title=re.sub(r'[\\/:*?"<>|]','_',p.get("title","product"))[:60].strip("_") or f"product_{p['product_no']:03d}"
                pdir=os.path.join(brand_folder,safe_title); os.makedirs(pdir,exist_ok=True)
                purl=p.get("url","")
                if not purl or not purl.startswith("http"): continue
                try:
                    req2=ur.Request(purl,headers=hdrs2)
                    with ur.urlopen(req2,timeout=12) as r2: pg_html=r2.read().decode("utf-8",errors="ignore")
                    soup2=BeautifulSoup(pg_html,"lxml"); img_count=0
                    for img in soup2.find_all("img",src=True):
                        src=img["src"]
                        if src.startswith("//"): src="https:"+src
                        elif src.startswith("/"): src=urllib.parse.urljoin(purl,src)
                        if not src.startswith("http"): continue
                        ext=src.split("?")[0].rsplit(".",1); ext=ext[-1].lower()[:4] if len(ext)>1 else "jpg"
                        if ext not in ("jpg","jpeg","png","webp","gif"): continue
                        try:
                            req3=ur.Request(src,headers=hdrs2)
                            with ur.urlopen(req3,timeout=8) as ri: data=ri.read()
                            if len(data)<1000: continue
                            out=os.path.join(pdir,f"img_{img_count:03d}.{ext}")
                            with open(out,"wb") as imgf: imgf.write(data)
                            img_count+=1
                            if img_count>=15: break
                        except: continue
                    if img_count: self._log(self.ec_log,f"  ✔ {safe_title[:30]}: {img_count} img(s)")
                except Exception as e: self._log(self.ec_log,f"  ⚠ {safe_title[:25]}: {e}")
        return products

    def _ec_csv(self):
        if not self._ec_prods: self.notif.push("Empty","Scrape products first.","warn"); return
        brand=getattr(self,"_ec_brand","brand"); folder=getattr(self,"_ec_folder",self.ec_save.get())
        cats=[p.get("category","") for p in self._ec_prods if p.get("category","") not in ("","N/A")]
        cat_name=cats[0] if cats else brand
        cat_name=re.sub(r'[\\/:*?"<>|]','_',cat_name)[:50].strip("_") or brand
        out=os.path.join(folder,f"{cat_name}.csv")
        fields=["product_no","category","title","price","sale_price","url","images","videos","description"]
        with open(out,"w",newline="",encoding="utf-8-sig") as csvf:
            w=csv.DictWriter(csvf,fieldnames=fields,extrasaction="ignore"); w.writeheader()
            sorted_p=sorted(self._ec_prods,key=lambda x:(x.get("category","zzz"),x.get("product_no",0)))
            w.writerows(sorted_p)
        self.notif.push("CSV Saved",out,"ok"); self._log(self.ec_log,f"✔ CSV: {out}")

    # ── TAB 5: ACCOUNT — P6 ──────────────────────────────
    def _tab_account(self,nb):
        f=tk.Frame(nb,bg=T["bg3"]); nb.add(f,text="  👤 Account  ")
        self._sec(f,"My Account","Profile, notes, and security")
        inner=self._scrolled_frame(f)
        users=load_users(); ud=users.get(self.username,{}); role=ud.get("role","user")

        # Avatar
        self._sh(inner,"🖼 Profile Photo")
        av_row=tk.Frame(inner,bg=T["bg3"]); av_row.pack(fill="x",padx=22,pady=8)
        self._av_lbl=tk.Label(av_row,bg=T["bg3"]); self._av_lbl.pack(side="left",padx=(0,14))
        self._load_av(ud.get("avatar",""))
        av_right=tk.Frame(av_row,bg=T["bg3"]); av_right.pack(side="left",fill="x",expand=True)
        self.av_e=tk.Entry(av_right,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                           relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        self.av_e.insert(0,ud.get("avatar","")); self.av_e.pack(fill="x",ipady=5); self._rc(self.av_e)
        br=tk.Frame(av_right,bg=T["bg3"]); br.pack(fill="x",pady=(6,0))
        def browse_av():
            p=filedialog.askopenfilename(filetypes=[("Image","*.png *.jpg *.jpeg *.gif")])
            if p: self.av_e.delete(0,"end"); self.av_e.insert(0,p); self._load_av(p); self._update_hdr_avatar(p)
        self._btn(br,"Browse Photo",browse_av,sm=True,side="left")
        self._btn(br,"Remove",lambda:(self.av_e.delete(0,"end"),self._load_av(""),self._update_hdr_avatar("")),sm=True,side="left",color=T["red"])
        self._btn(inner,"💾  Save Photo",self._save_avatar_only,sm=True)

        # Profile info
        self._sh(inner,"📝 Profile Info")
        self._acc={}
        for label,key in [("Name","display_name"),("Email","email"),("Phone","phone"),("Date of Birth","dob"),("Bio","bio")]:
            row=tk.Frame(inner,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=3)
            tk.Label(row,text=label+":",font=self._F(10,True),fg=T["text"],bg=T["bg3"],width=16,anchor="w").pack(side="left")
            e=tk.Entry(row,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                       relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
            e.insert(0,ud.get(key,"")); e.pack(side="left",fill="x",expand=True,padx=4,ipady=5)
            self._acc[key]=e; self._rc(e)

        # Notes
        self._sh(inner,"📋 Notes & To-Do")
        tk.Label(inner,text="Personal reminders — shown as notification on startup.",
                 font=self._F(9),fg=T["muted"],bg=T["bg3"]).pack(anchor="w",padx=22,pady=(0,4))
        self.notes_box=tk.Text(inner,height=7,font=self._FF(),bg=T["bg4"],fg=T["text"],
                               insertbackground=T["acc"],relief="flat",
                               highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        self.notes_box.pack(fill="x",padx=22,pady=(0,2))
        notes=ud.get("notes","")
        if isinstance(notes,list): notes="\n".join(notes)
        self.notes_box.insert("1.0",notes); self._rct(self.notes_box)
        self._btn(inner,"💾  Save Notes",self._save_notes_only,sm=True)

        # Security
        self._sh(inner,"🔒 Security")
        hr=tk.Frame(inner,bg=T["bg3"]); hr.pack(fill="x",padx=22,pady=3)
        tk.Label(hr,text="Password Hint:",font=self._F(10,True),fg=T["text"],bg=T["bg3"],width=16,anchor="w").pack(side="left")
        self.hint_e=tk.Entry(hr,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],
                             relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        self.hint_e.insert(0,ud.get("pw_hint","")); self.hint_e.pack(side="left",fill="x",expand=True,padx=4,ipady=5); self._rc(self.hint_e)
        phrases=ud.get("recovery_phrases","")
        if phrases:
            pf=tk.Frame(inner,bg=T["bg4"]); pf.pack(fill="x",padx=22,pady=(4,0))
            tk.Label(pf,text="Recovery Phrases:",font=self._F(9,True),fg=T["yellow"],bg=T["bg4"]).pack(anchor="w",padx=10,pady=(6,2))
            tk.Label(pf,text=phrases,font=("Consolas",8),fg=T["yellow"],bg=T["bg4"],wraplength=700,justify="left").pack(anchor="w",padx=10,pady=(0,6))
        self._btn(inner,"🔒  Change Password",self._change_pw,full=True,color=T["acc2"])
        if role=="admin":
            self._sh(inner,"👑 Admin Panel")
            self._btn(inner,"Manage All Users",self._admin_panel,full=True,color=T["yellow"])
        self._sh(inner,"💾 Save All")
        self._btn(inner,"💾  Save All Profile Info",self._save_profile,full=True,color=T["acc"])
        self._btn(inner,"🗑  Delete Account",self._del_account,full=True,color=T["red"])
        if notes.strip(): self.root.after(1500,lambda:self.notif.push("📋 Notes",notes.strip()[:60],"info",6000))

    def _load_av(self,path):
        if path and Path(path).exists():
            try:
                from PIL import Image,ImageTk
                if path.lower().endswith(".gif"):
                    self._av_gif=[]; gif=Image.open(path)
                    try:
                        while True: self._av_gif.append(ImageTk.PhotoImage(gif.copy().resize((80,80)))); gif.seek(gif.tell()+1)
                    except EOFError: pass
                    def anim(i=0):
                        try:
                            if self._av_gif and self._av_lbl.winfo_exists():
                                self._av_lbl.config(image=self._av_gif[i]); self._av_lbl.after(80,anim,(i+1)%len(self._av_gif))
                        except: pass
                    anim(); return
                im=Image.open(path).resize((80,80)); self._av_img=ImageTk.PhotoImage(im)
                self._av_lbl.config(image=self._av_img,text="",font=("Segoe UI",1)); return
            except: pass
        self._av_lbl.config(image="",text="👤",font=("Segoe UI",36),fg=T["muted"],bg=T["bg3"])

    def _update_hdr_avatar(self,path):
        """P6: Update avatar in header when changed in account tab."""
        self._load_hdr_avatar(path)

    def _save_avatar_only(self):
        users=load_users(); u=users.get(self.username,{})
        u["avatar"]=self.av_e.get().strip(); users[self.username]=u; save_users(users)
        self._update_hdr_avatar(u["avatar"]); self.notif.push("Saved","Profile photo saved.","ok")

    def _save_notes_only(self):
        users=load_users(); u=users.get(self.username,{})
        u["notes"]=self.notes_box.get("1.0","end").strip(); users[self.username]=u; save_users(users)
        self.notif.push("Saved","Notes saved.","ok")

    def _save_profile(self):
        users=load_users(); u=users.get(self.username,{})
        for key,e in self._acc.items(): u[key]=e.get().strip()
        u["full_name"]=u.get("display_name",""); u["avatar"]=self.av_e.get().strip()
        u["pw_hint"]=self.hint_e.get().strip(); u["notes"]=self.notes_box.get("1.0","end").strip()
        users[self.username]=u; save_users(users)
        self._update_hdr_avatar(u["avatar"]); self.notif.push("Saved","All profile info saved.","ok")

    def _change_pw(self):
        d=InputDialog(self.root,"Change Password","Current password:","•"); old=d.wait()
        if not old: return
        users=load_users()
        if users[self.username]["pw"]!=hpw(old): AppDialog(self.root,"Error","Wrong current password.",("OK",),"✕").wait(); return
        d2=InputDialog(self.root,"New Password","New password (min 4 chars):","•"); new=d2.wait()
        if not new or len(new)<4: AppDialog(self.root,"Error","Password too short.",("OK",),"✕").wait(); return
        users[self.username]["pw"]=hpw(new); save_users(users); self.notif.push("Done","Password changed.","ok")

    def _del_account(self):
        d=AppDialog(self.root,"Delete Account",f"Delete @{self.username} and all data?",("Cancel","Delete"),"⚠")
        if d.wait()!="Delete": return
        d2=InputDialog(self.root,"Confirm","Enter your password:","•"); pw=d2.wait()
        if not pw: return
        users=load_users()
        if users[self.username]["pw"]!=hpw(pw): AppDialog(self.root,"Error","Wrong password.",("OK",),"✕").wait(); return
        del users[self.username]; save_users(users)
        try: shutil.rmtree(self.udir_)
        except: pass
        app_dir=self.app_dir; self.root.withdraw()
        try: new_user=LoginWindow(app_dir).run()
        finally:
            try: self.root.destroy()
            except: pass
        if new_user: NexFetchApp(new_user,app_dir).run()

    def _admin_panel(self):
        win=tk.Toplevel(self.root); win.title("Admin Panel"); win.geometry("700x500"); win.configure(bg=T["bg"]); win.grab_set()
        tk.Label(win,text="👑 Admin — All Users",font=("Segoe UI",14,"bold"),fg=T["acc"],bg=T["bg"]).pack(pady=12)
        users=load_users()
        box=scrolledtext.ScrolledText(win,font=("Consolas",9),bg=T["bg2"],fg=T["text"],height=14,relief="flat")
        box.pack(fill="both",expand=True,padx=16,pady=8)
        for uname,ud in users.items():
            box.insert("end",f"  @{uname}  [{ud.get('role','user')}]  {ud.get('display_name','')}  {ud.get('email','')}  created {ud.get('created','')[:10]}\n\n")
        def reset():
            d=InputDialog(win,"Reset Password","Username to reset:"); uname=d.wait()
            if not uname or uname not in users: return
            d2=InputDialog(win,"New Password",f"New password for @{uname}:","•"); npw=d2.wait()
            if not npw: return
            users[uname]["pw"]=hpw(npw); save_users(users); self.notif.push("Done",f"Password reset for @{uname}","ok")
        def delete():
            d=InputDialog(win,"Delete User","Username to delete:"); uname=d.wait()
            if not uname or uname==self.username: return
            if uname not in users: return
            d2=AppDialog(win,"Confirm",f"Delete @{uname}?",("Cancel","Delete"),"⚠")
            if d2.wait()=="Delete":
                del users[uname]; save_users(users)
                try: shutil.rmtree(udir(uname))
                except: pass
                self.notif.push("Deleted",f"@{uname} removed","ok")
        bf=tk.Frame(win,bg=T["bg"]); bf.pack(pady=8)
        tk.Button(bf,text="Reset Password",command=reset,font=("Segoe UI",10,"bold"),bg=T["yellow"],fg=T["bg"],relief="flat",padx=12,pady=6,cursor="hand2").pack(side="left",padx=6)
        tk.Button(bf,text="Delete User",command=delete,font=("Segoe UI",10,"bold"),bg=T["red"],fg=T["text"],relief="flat",padx=12,pady=6,cursor="hand2").pack(side="left",padx=6)

    # ── TAB 6: SETTINGS ───────────────────────────────────
    def _tab_settings(self,nb):
        is_admin=self._role=="admin"
        f=tk.Frame(nb,bg=T["bg3"]); nb.add(f,text="  ⚙ Settings  ")
        self._sec(f,"Settings","Admin: full access  ·  User: download folder & maintenance only")
        inner=self._scrolled_frame(f)
        self._sh(inner,"📁 Download Folder")
        self._sr_dir(inner,"Download path:","s_dlpath",self.cfg.get("dl_path",""))
        self._sh(inner,"🔧 Maintenance")
        self._btn(inner,"⬆  Update yt-dlp",self._upd_ytdlp,full=True,color=T["yellow"])
        self._btn(inner,"🔧  Re-download ffmpeg",self._fix_ff,full=True,color=T["yellow"])
        self._btn(inner,"🔄  Re-run Setup",self._rerun,full=True)
        self._btn(inner,"🗑  Clear All Logs",self._clear_logs,full=True,color=T["red"])
        self._btn(inner,"💾  Save Settings",self._save_st,full=True,color=T["acc"])
        if not is_admin: return
        self._sh(inner,"🪪 Identity")
        for lbl,attr,val in [("Tool Name","s_name",self.cfg["tool_name"]),("Author","s_author",self.cfg["author"]),("Version","s_ver",self.cfg["version"]),("License","s_lic",self.cfg["license"])]:
            self._sr_entry(inner,lbl,attr,val)
        self._sh(inner,"🔐 Access Control")
        am=tk.Frame(inner,bg=T["bg3"]); am.pack(fill="x",padx=22,pady=4)
        tk.Label(am,text="Admin-only registration:",font=self._F(10,True),fg=T["text"],bg=T["bg3"],width=26,anchor="w").pack(side="left")
        self.s_admin_mode=tk.BooleanVar(value=self.cfg.get("admin_mode",False))
        tk.Checkbutton(am,variable=self.s_admin_mode,bg=T["bg3"],fg=T["acc"],selectcolor=T["bg4"],activebackground=T["bg3"]).pack(side="left")
        self._sh(inner,"🎟 Invite Codes (one per line)")
        codes=self.cfg.get("invite_codes",["NEXFETCH2024"])
        if isinstance(codes,str): codes=[codes]
        self.s_codes=tk.Text(inner,height=4,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        self.s_codes.insert("1.0","\n".join(codes)); self.s_codes.pack(fill="x",padx=22,pady=(0,4))
        gr=tk.Frame(inner,bg=T["bg3"]); gr.pack(fill="x",padx=22,pady=(0,4))
        def gen_code():
            new="NX-"+"".join(random.choices(string.ascii_uppercase+string.digits,k=8))
            self.s_codes.insert("end",f"\n{new}")
        self._btn(gr,"+ Generate Code",gen_code,sm=True,side="left",color=T["cyan"])
        self._sh(inner,"🎨 Colors — click to change")
        self._color_sw={}
        for lbl,key in [("Background","bg"),("BG Panel","bg2"),("BG Tab","bg3"),("BG Card","bg4"),
                        ("Accent Red","acc"),("Accent Hover","acc2"),("Accent Dark","acc3"),
                        ("Text","text"),("Muted","muted"),("Log text","log_fg"),("Log BG","log_bg")]:
            row=tk.Frame(inner,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=2)
            tk.Label(row,text=lbl+":",font=self._F(10,True),fg=T["text"],bg=T["bg3"],width=18,anchor="w").pack(side="left")
            col=self.cfg.get(key,T.get(key,"#000000"))
            sw=tk.Label(row,text=f"  {col}  ",font=("Consolas",9),bg=col,fg="#fff",relief="flat",padx=6,pady=3,cursor="hand2")
            sw.pack(side="left",padx=4); sw.bind("<Button-1>",lambda e,k=key,s=sw:self._pick_color(k,s)); self._color_sw[key]=sw
        self._sh(inner,"🔤 Font")
        frow=tk.Frame(inner,bg=T["bg3"]); frow.pack(fill="x",padx=22,pady=4)
        tk.Label(frow,text="Family:",font=self._F(10,True),fg=T["text"],bg=T["bg3"],width=12,anchor="w").pack(side="left")
        self.s_ff=ttk.Combobox(frow,values=["Segoe UI","Consolas","Arial","Verdana","Courier New","Tahoma","Calibri"],width=18,state="readonly")
        self.s_ff.set(self.cfg.get("font_family","Segoe UI")); self.s_ff.pack(side="left",padx=4)
        tk.Label(frow,text="Size:",font=self._F(10,True),fg=T["text"],bg=T["bg3"]).pack(side="left",padx=(16,4))
        self.s_fs=ttk.Combobox(frow,values=["8","9","10","11","12"],width=6,state="readonly")
        self.s_fs.set(str(self.cfg.get("font_size",9))); self.s_fs.pack(side="left")
        self._sh(inner,"🖼 Assets")
        self._sr_browse(inner,"Logo (PNG/ICO/GIF):","s_logo",self.cfg.get("logo_path",""),[("Image","*.png *.ico *.jpg *.gif")])
        self._sr_browse(inner,"Background (PNG/JPG/GIF):","s_bgimg",self.cfg.get("bg_image",""),[("Image","*.png *.jpg *.gif")])
        self._btn(inner,"💾  Save All Settings",self._save_st,full=True,color=T["acc"])

    def _sr_entry(self,parent,label,attr,val):
        row=tk.Frame(parent,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=3)
        tk.Label(row,text=label+":",font=self._F(10,True),fg=T["text"],bg=T["bg3"],width=18,anchor="w").pack(side="left")
        e=tk.Entry(row,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        e.insert(0,val); e.pack(side="left",fill="x",expand=True,padx=4,ipady=4); setattr(self,attr,e)

    def _sr_browse(self,parent,label,attr,val,ft):
        row=tk.Frame(parent,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=4)
        tk.Label(row,text=label,font=self._F(10,True),fg=T["text"],bg=T["bg3"],width=24,anchor="w").pack(side="left")
        e=tk.Entry(row,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        e.insert(0,val); e.pack(side="left",fill="x",expand=True,padx=4,ipady=4); setattr(self,attr,e)
        self._btn(row,"Browse",lambda:self._browse_file(e,ft),sm=True,side="left")
        self._btn(row,"✕",lambda:e.delete(0,"end"),sm=True,side="left")

    def _sr_dir(self,parent,label,attr,val):
        row=tk.Frame(parent,bg=T["bg3"]); row.pack(fill="x",padx=22,pady=4)
        tk.Label(row,text=label,font=self._F(10,True),fg=T["text"],bg=T["bg3"],width=24,anchor="w").pack(side="left")
        e=tk.Entry(row,font=self._FF(),bg=T["bg4"],fg=T["text"],insertbackground=T["acc"],relief="flat",highlightthickness=1,highlightbackground=T["border"],highlightcolor=T["acc"])
        e.insert(0,val); e.pack(side="left",fill="x",expand=True,padx=4,ipady=4); setattr(self,attr,e)
        self._btn(row,"Browse",lambda:self._browse_dir(e),sm=True,side="left")

    def _pick_color(self,key,swatch):
        r=colorchooser.askcolor(color=self.cfg.get(key,"#000000"),title=f"Pick: {key}")
        if r and r[1]: self.cfg[key]=r[1]; T[key]=r[1]; swatch.config(bg=r[1],text=f"  {r[1]}  ")

    def _save_st(self):
        self.cfg["dl_path"]=self.s_dlpath.get().strip() or self.cfg["dl_path"]; self._save_ucfg()
        if self._role=="admin":
            for attr,key in [("s_name","tool_name"),("s_author","author"),("s_ver","version"),("s_lic","license")]:
                if hasattr(self,attr): self.cfg[key]=getattr(self,attr).get().strip() or self.cfg[key]
            if hasattr(self,"s_admin_mode"): self.cfg["admin_mode"]=self.s_admin_mode.get()
            if hasattr(self,"s_codes"):
                codes=[c.strip() for c in self.s_codes.get("1.0","end").splitlines() if c.strip()]
                self.cfg["invite_codes"]=codes or ["NEXFETCH2024"]
            if hasattr(self,"s_ff"): self.cfg["font_family"]=self.s_ff.get()
            if hasattr(self,"s_fs"):
                try: self.cfg["font_size"]=int(self.s_fs.get())
                except: pass
            if hasattr(self,"s_logo"): self.cfg["logo_path"]=self.s_logo.get().strip()
            if hasattr(self,"s_bgimg"): self.cfg["bg_image"]=self.s_bgimg.get().strip()
        save_cfg(self.cfg); self.notif.push("Saved","Settings saved. Restart to apply visual changes.","ok")

    def _upd_ytdlp(self):
        ov=LoadingOverlay(self.root,"Updating yt-dlp...")
        def run():
            r=subprocess.run([sys.executable,"-m","pip","install","yt-dlp","--upgrade","--quiet"],capture_output=True,text=True,creationflags=FLAGS)
            self.root.after(0,ov.destroy); ok=r.returncode==0
            self.root.after(0,lambda:self.notif.push("yt-dlp Updated" if ok else "Update Failed","","ok" if ok else "error"))
        threading.Thread(target=run,daemon=True).start()

    def _fix_ff(self):
        ov=LoadingOverlay(self.root,"Downloading ffmpeg...")
        def run():
            try:
                import zipfile
                ff_dir=self.app_dir/"ffmpeg_bin"; ff_dir.mkdir(exist_ok=True)
                url="https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                zp=self.app_dir/"ffmpeg_tmp.zip"; urllib.request.urlretrieve(url,zp)
                with zipfile.ZipFile(zp,"r") as z:
                    for m in z.namelist():
                        fn=Path(m).name
                        if fn in ("ffmpeg.exe","ffprobe.exe"):
                            with z.open(m) as s,open(ff_dir/fn,"wb") as d: shutil.copyfileobj(s,d)
                zp.unlink(missing_ok=True); os.environ["PATH"]=str(ff_dir)+os.pathsep+os.environ.get("PATH","")
                self.root.after(0,ov.destroy); self.root.after(0,lambda:self.notif.push("ffmpeg","Downloaded.","ok"))
            except Exception as e:
                self.root.after(0,ov.destroy); self.root.after(0,lambda:self.notif.push("ffmpeg Error",str(e)[:50],"error"))
        threading.Thread(target=run,daemon=True).start()

    def _rerun(self):
        d=AppDialog(self.root,"Re-run Setup","Re-install all dependencies?",("Cancel","Yes"),"🔄")
        if d.wait()=="Yes":
            flag=self.app_dir/".setup_complete"
            if flag.exists(): flag.unlink()
            AppDialog(self.root,"Restart Required","Close and reopen NexFetch.",("OK",),"ℹ").wait()

    def _clear_logs(self):
        for attr in ["dl_log","mu_log","sc_log","ec_log"]:
            box=getattr(self,attr,None)
            if box:
                try: box.configure(state="normal"); box.delete("1.0","end"); box.configure(state="disabled")
                except: pass
        self.notif.push("Cleared","All logs cleared.","ok")

    def run(self): self.root.mainloop()
