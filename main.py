import math
import random
from pyodide.ffi import create_proxy
from js import document, window, console, localStorage, requestAnimationFrame, Math, Event

class MirrorGarden:
    def __init__(self):
        self.canvas = document.getElementById('game-canvas')
        self.ctx = self.canvas.getContext('2d')
        self.left_anchor = document.getElementById('left-anchor')
        self.left_barrier = document.getElementById('left-barrier')
        self.reward_ui = document.getElementById('reward-ui')
        self.reward_text = document.getElementById('reward-text')
        self.flower_container = document.getElementById('flower-container')
        self.next_btn = document.getElementById('next-btn')
        self.unlock_instruction = document.getElementById('unlock-instruction')
        
        self.mode = "A" # Start with A
        self.state = "DRAWING" # States: DRAWING, WAITING_LEFT, REWARD
        self.is_drawing = False
        self.paths = []
        self.target_path = []
        self.target_covered = []
        self.left_unlock_target = None # (x, y, radius)
        
        self.last_left_attention_time = window.performance.now()
        
        self.praise_phrases = [
            "媽，這朵花送妳！", "妳今天畫得真美！", "眼神越來越準了喔！", "太棒了，繼續保持！",
            "這幅畫很有藝術感呢！", "左邊也注意到了，很厲害！", "進步神速！", "真的很漂亮！",
            "完美對稱，太好看了！", "就像真正的畫家一樣！", "手很穩喔！", "這顏色配得真好！",
            "注意力越來越集中了！", "又完成了一幅大作！", "太有耐心了！", "畫得非常流暢！",
            "這朵玫瑰為妳綻放！", "眼明手快，繼續加油！", "今天的表現滿分！", "看著這朵花，心情都好了！"
        ]
        
        self.bind_events()
        self.update_canvas_size()
        self.debug_self_test()
        
        self.reset_level()
        
        self.render_proxy = create_proxy(self.render)
        requestAnimationFrame(self.render_proxy)

    def debug_self_test(self):
        console.log("[Self-Test] PyScript Environment OK. No global pollution.")
        try:
            localStorage.setItem("test_key", "test_val")
            val = localStorage.getItem("test_key")
            localStorage.removeItem("test_key")
            console.log(f"[Self-Test] LocalStorage OK: {val}")
        except Exception as e:
            console.error(f"[Self-Test] LocalStorage Error: {e}")
            
    def update_canvas_size(self):
        self.width = window.innerWidth
        self.height = window.innerHeight
        self.canvas.width = self.width
        self.canvas.height = self.height

    def bind_events(self):
        self.resize_proxy = create_proxy(lambda e: self.update_canvas_size())
        window.addEventListener('resize', self.resize_proxy)
        
        self.touch_start_proxy = create_proxy(self.on_touch_start)
        self.touch_move_proxy = create_proxy(self.on_touch_move)
        self.touch_end_proxy = create_proxy(self.on_touch_end)
        
        # Touch
        self.canvas.addEventListener('touchstart', self.touch_start_proxy, {"passive": False})
        self.canvas.addEventListener('touchmove', self.touch_move_proxy, {"passive": False})
        self.canvas.addEventListener('touchend', self.touch_end_proxy)
        self.canvas.addEventListener('touchcancel', self.touch_end_proxy)
        
        # Mouse (for desktop testing)
        self.canvas.addEventListener('mousedown', self.touch_start_proxy)
        self.canvas.addEventListener('mousemove', self.touch_move_proxy)
        self.canvas.addEventListener('mouseup', self.touch_end_proxy)
        
        # UI
        self.next_btn_proxy = create_proxy(self.next_level)
        self.next_btn.addEventListener('click', self.next_btn_proxy)

    def generate_lissajous_path(self):
        points = []
        A = self.width / 4 - 50
        B = self.height / 2 - 50
        center_x = self.width * 0.75
        center_y = self.height / 2
        
        a_param = random.choice([1, 2, 3])
        b_param = random.choice([1, 2, 3])
        if a_param == b_param: b_param += 1
        delta = math.pi / 2
        
        for i in range(200):
            t = i * (math.pi * 2) / 100
            x = center_x + A * math.sin(a_param * t + delta)
            y = center_y + B * math.sin(b_param * t)
            points.append((x, y))
        return points

    def generate_object_path(self):
        points = []
        shape_type = random.randint(0, 4)
        center_x = self.width * 0.75
        center_y = self.height / 2
        radius = min(self.width/4, self.height/2) - 40
        
        if shape_type == 0: # Polygon
            sides = random.randint(3, 8)
            offset_angle = random.random() * math.pi
            for i in range(sides + 1):
                angle = offset_angle + i * (math.pi * 2) / sides
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                points.append((x, y))
        elif shape_type == 1: # Star
            points_count = random.randint(4, 8)
            inner_radius = radius * random.uniform(0.3, 0.6)
            offset_angle = random.random() * math.pi
            for i in range(points_count * 2 + 1):
                angle = offset_angle + i * (math.pi) / points_count
                r = radius if i % 2 == 0 else inner_radius
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                points.append((x, y))
        elif shape_type == 2: # Spiral
            loops = random.randint(2, 4)
            for i in range(150):
                t = i / 150.0
                angle = t * math.pi * 2 * loops
                r = radius * t
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                points.append((x, y))
        elif shape_type == 3: # Heart
            scale = radius / 16.0
            for i in range(0, 101):
                t = i * (math.pi * 2) / 100
                x = center_x + scale * 16 * math.sin(t)**3
                y = center_y - scale * (13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                points.append((x, y))
        else: # Superellipse
            n = random.uniform(0.3, 2.5)
            a = radius
            b = radius * random.uniform(0.6, 1.2)
            for i in range(101):
                t = i * (math.pi * 2) / 100
                cos_t = math.cos(t)
                sin_t = math.sin(t)
                x_val = math.copysign(a * (abs(cos_t) ** (2/n)), cos_t)
                y_val = math.copysign(b * (abs(sin_t) ** (2/n)), sin_t)
                points.append((center_x + x_val, center_y + y_val))
        return points

    def reset_level(self):
        self.state = "DRAWING"
        self.left_unlock_target = None
        self.unlock_instruction.style.display = "none"
        self.paths = []
        self.target_path = []
        self.target_covered = []
        
        if self.mode == "A":
            self.target_path = self.generate_lissajous_path()
            self.target_covered = [False] * len(self.target_path)
        elif self.mode == "B":
            self.target_path = self.generate_object_path()
            self.target_covered = [False] * len(self.target_path)
        
        self.last_left_attention_time = window.performance.now()

    def check_left_attention(self, x):
        if x < self.width / 2:
            self.last_left_attention_time = window.performance.now()
            
    def update_coverage(self, x, y):
        if self.state != "DRAWING" or not self.target_path: return
        threshold = 65 # increased pixel distance for easier tracing
        for i, (tx, ty) in enumerate(self.target_path):
            if not self.target_covered[i]:
                dist = math.hypot(x - tx, y - ty)
                if dist < threshold:
                    self.target_covered[i] = True

    def get_coords(self, e):
        if getattr(e, "touches", None) and e.touches.length > 0:
            return e.touches.item(0).clientX, e.touches.item(0).clientY
        return e.clientX, e.clientY

    def on_touch_start(self, e):
        e.preventDefault()
        if self.state == "REWARD": return
        
        x, y = self.get_coords(e)
        self.check_left_attention(x)
        
        if self.state == "WAITING_LEFT":
            self.check_left_unlock(x, y)
            return
            
        self.is_drawing = True
        self.paths.append([(x, y)])
        self.update_coverage(x, y)
        
    def on_touch_move(self, e):
        e.preventDefault()
        if not self.is_drawing or self.state == "REWARD": return
            
        x, y = self.get_coords(e)
        
        if self.state == "WAITING_LEFT":
             self.check_left_unlock(x, y)
             return
             
        if len(self.paths) > 0:
            self.paths[-1].append((x, y))
            self.check_left_attention(x)
            self.update_coverage(x, y)
            
    def on_touch_end(self, e):
        self.is_drawing = False
        
    def draw_target_path(self):
        if not self.target_path: return
        self.ctx.beginPath()
        self.ctx.strokeStyle = "rgba(255, 255, 255, 0.2)"
        self.ctx.lineWidth = 15
        self.ctx.lineCap = "round"
        self.ctx.lineJoin = "round"
        self.ctx.moveTo(self.target_path[0][0], self.target_path[0][1])
        for i in range(1, len(self.target_path)):
            self.ctx.lineTo(self.target_path[i][0], self.target_path[i][1])
        self.ctx.stroke()
        
    def draw_mirrored_paths(self):
        for path in self.paths:
            if len(path) < 2: continue
            
            # Original trace (Right)
            self.ctx.beginPath()
            self.ctx.strokeStyle = "rgba(150, 150, 150, 0.6)"
            self.ctx.lineWidth = 5
            self.ctx.lineCap = "round"
            self.ctx.lineJoin = "round"
            self.ctx.moveTo(path[0][0], path[0][1])
            for i in range(1, len(path)):
                self.ctx.lineTo(path[i][0], path[i][1])
            self.ctx.stroke()
            
            # Mirrored trace (Left)
            self.ctx.beginPath()
            t = window.performance.now() / 1000.0
            r = int(127 * math.sin(t*2) + 128)
            g = int(127 * math.sin(t*2 + 2) + 128)
            b = int(127 * math.sin(t*2 + 4) + 128)
            self.ctx.strokeStyle = f"rgba({r}, {max(150, g)}, 255, 1.0)"
            self.ctx.lineWidth = 12
            self.ctx.lineCap = "round"
            self.ctx.lineJoin = "round"
            self.ctx.shadowBlur = 20
            self.ctx.shadowColor = "#FFFF00"
            
            self.ctx.moveTo(self.width - path[0][0], path[0][1])
            for i in range(1, len(path)):
                self.ctx.lineTo(self.width - path[i][0], path[i][1])
            self.ctx.stroke()
            self.ctx.shadowBlur = 0
            
    def draw_unlock_target(self, time):
        if self.state != "WAITING_LEFT" or not self.left_unlock_target: return
        x, y, base_r = self.left_unlock_target
        
        # Pulsing radius
        pulse = math.sin(time / 150.0) * 10
        r = base_r + pulse
        
        self.ctx.beginPath()
        self.ctx.arc(x, y, r, 0, math.pi * 2)
        self.ctx.fillStyle = "#FF3366"
        self.ctx.shadowBlur = 30
        self.ctx.shadowColor = "#FF0000"
        self.ctx.fill()
        
        # Inner white core
        self.ctx.beginPath()
        self.ctx.arc(x, y, base_r * 0.4, 0, math.pi * 2)
        self.ctx.fillStyle = "#FFFFFF"
        self.ctx.fill()
        self.ctx.shadowBlur = 0
            
    def check_attention_timeout(self, current_time):
        if self.state != "DRAWING": return
        # Left barrier wave effect if drawing on right but ignoring left for 5s
        if current_time - self.last_left_attention_time > 5000 and self.is_drawing:
            self.left_barrier.classList.add("wave-barrier-active")
            self.left_anchor.classList.add("wave-effect")
        else:
            self.left_barrier.classList.remove("wave-barrier-active")
            self.left_anchor.classList.remove("wave-effect")
            
    def render(self, time):
        self.ctx.fillStyle = "black"
        self.ctx.fillRect(0, 0, self.width, self.height)
        
        self.draw_target_path()
        self.draw_mirrored_paths()
        self.draw_unlock_target(time)
        self.check_attention_timeout(time)
        
        # Check success condition (Transition to WAITING_LEFT)
        if self.state == "DRAWING":
            if self.mode in ["A", "B"] and len(self.target_path) > 0:
                coverage_percent = sum(self.target_covered) / len(self.target_covered)
                if coverage_percent > 0.80:  # 80% covered
                    self.spawn_left_target()
            elif self.mode == "C":
                total_points = sum(len(p) for p in self.paths)
                if total_points > 150: 
                    self.spawn_left_target()
                    
        requestAnimationFrame(self.render_proxy)
        
    def spawn_left_target(self):
        self.state = "WAITING_LEFT"
        self.unlock_instruction.style.display = "block"
        self.is_drawing = False
        target_x = random.uniform(50, self.width * 0.2) # Far left 20%
        target_y = random.uniform(100, self.height - 100)
        self.left_unlock_target = (target_x, target_y, 40) # x, y, radius
        console.log("Spawned left target at", target_x, target_y)

    def check_left_unlock(self, x, y):
        if not self.left_unlock_target: return
        tx, ty, r = self.left_unlock_target
        dist = math.hypot(x - tx, y - ty)
        # Give a generous hit radius for the unlock target
        if dist < r + 40: 
            self.left_unlock_target = None
            self.trigger_reward()
        
    def trigger_reward(self):
        self.state = "REWARD"
        self.unlock_instruction.style.display = "none"
        phrase = random.choice(self.praise_phrases)
        self.reward_text.innerText = phrase
        
        flower_svg = """
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:100%; animation: bloom 2s ease-out;">
            <style>
                @keyframes bloom { 
                    0% { transform: scale(0) rotate(-45deg); opacity: 0; } 
                    100% { transform: scale(1) rotate(0deg); opacity: 1; } 
                }
            </style>
            <path d="M50,50 C20,10 10,40 50,50" fill="#ff0055" />
            <path d="M50,50 C80,10 90,40 50,50" fill="#ee0044" />
            <path d="M50,50 C10,80 40,90 50,50" fill="#dd0033" />
            <path d="M50,50 C90,80 60,90 50,50" fill="#cc0022" />
            <circle cx="50" cy="50" r="10" fill="#ffcc00" />
        </svg>
        """
        self.flower_container.innerHTML = flower_svg
        self.reward_ui.classList.add("visible")
        self.is_drawing = False
        
    def next_level(self, *args):
        self.reward_ui.classList.remove("visible")
        # Cycle modes!
        if self.mode == "A":
            self.mode = "B"
        elif self.mode == "B":
            self.mode = "C"
        else:
            self.mode = "A"
        console.log("Starting Mode " + self.mode)
        self.reset_level()

app = MirrorGarden()
