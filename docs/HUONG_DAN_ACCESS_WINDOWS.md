# 🌐 Hướng Dẫn Access Frontend Từ Windows

## ✅ Hệ Thống Đã Sẵn Sàng!

Backend và Frontend đã chạy trên server. Bây giờ bạn cần kết nối từ máy Windows.

---

## 📋 Thông Tin Server

- **Server IP**: `192.168.28.32` (LAN) / `2a09:bac5:d46a:2e1e::498:2d` (IPv6)
- **Backend**: Port 8000
- **Frontend**: Port 8007

---

## 🔒 PHƯƠNG PHÁP 1: SSH Port Forwarding (KHUYẾN NGHỊ)

### Bước 1: Mở PowerShell trên Windows

Nhấn `Win + X` → chọn **"Windows PowerShell"** hoặc **"Terminal"**

### Bước 2: Tạo SSH Tunnel

```powershell
ssh -L 18007:localhost:8007 -L 18000:localhost:8000 ir@192.168.28.32
```

**Giải thích:**
- `-L 18007:localhost:8007` → Forward port frontend
- `-L 18000:localhost:8000` → Forward port backend
- Nhập password khi được yêu cầu
- **QUAN TRỌNG**: Giữ terminal này mở trong suốt quá trình sử dụng!

### Bước 3: Mở Browser

Mở **Google Chrome** hoặc **Edge**, truy cập:

```
http://localhost:18007
```

### Bước 4: Sử Dụng Sequential Query

1. **Tìm toggle switch** ở left panel: 🔗 **"Multi-Step Query Mode"**
2. **Check vào box** để enable
3. **Nhập queries**:
   - Bạn sẽ thấy 2 ô input mặc định
   - Click **➕** để thêm steps (tối đa 10)
   - Click **➖** để xóa steps (tối thiểu 2)
   
4. **Ví dụ 5-step query** (DRES example):
   ```
   Step 1: news story online scams malicious links
   Step 2: female interviewer woman reporter
   Step 3: aerial view trees mountain rocky mountainside
   Step 4: aerial shot trees rocky cliff mountain
   Step 5: girls selfie sticks Guizhou China
   ```

5. **Adjust settings** (optional):
   - Slider "Results to show": 10-100 (default 50)
   - Checkbox "Require all steps": Để OFF cho recall tốt hơn

6. **Click "🔍 Search Sequential Query"**

7. **Xem kết quả** (~1-2 giây):
   - **Step badges**: ✓1 ✓2 ✓3 ✓4 ✓5 (matched steps)
   - **Green border**: Complete match (100%)
   - **Yellow border**: Partial match (60-99%)
   - **Progress bar**: Visual completeness
   - **Score**: Số ở góc trên phải

---

## 🖥️ PHƯƠNG PHÁP 2: Dùng PuTTY (Nếu Bạn Quen PuTTY)

### Bước 1: Mở PuTTY

### Bước 2: Config Session
- **Host Name**: `192.168.28.32`
- **Port**: `22`
- **Connection type**: SSH

### Bước 3: Setup Tunnels
1. Sidebar → **Connection** → **SSH** → **Tunnels**
2. Add tunnel 1:
   - **Source port**: `18007`
   - **Destination**: `localhost:8007`
   - Click **Add**
3. Add tunnel 2:
   - **Source port**: `18000`
   - **Destination**: `localhost:8000`
   - Click **Add**

### Bước 4: Connect
- Click **Open**
- Login với username: `ir`
- **GIỮ CỬA SỔ PUTTY MỞ**

### Bước 5: Mở Browser
```
http://localhost:18007
```

---

## 🐛 Troubleshooting

### Problem 1: "Cannot connect to localhost:18007"

**Nguyên nhân**: SSH tunnel chưa được tạo hoặc đã đóng

**Giải pháp**:
```powershell
# Check xem port có listening không
netstat -an | findstr "18007"

# Nếu không thấy gì, tạo lại SSH tunnel
ssh -L 18007:localhost:8007 -L 18000:localhost:8000 ir@192.168.28.32
```

### Problem 2: "Frontend loading quá lâu"

**Nguyên nhân**: Backend không accessible hoặc CORS issue

**Giải pháp**:
1. Check backend qua tunnel:
   ```
   http://localhost:18000/health
   ```
   
2. Mở Browser Console (F12), check lỗi

3. Hard refresh: `Ctrl + Shift + R`

### Problem 3: "Sequential query không có kết quả"

**Nguyên nhân**: Queries quá strict hoặc không match

**Giải pháp**:
1. Giảm số steps (5 → 3)
2. Tắt "Require all steps"
3. Tăng top_k lên 100
4. Dùng queries đơn giản hơn:
   ```
   Step 1: person walking
   Step 2: person sitting
   Step 3: person standing
   ```

### Problem 4: "Images không hiển thị"

**Nguyên nhân**: Keyframe path issue

**Giải pháp**: Images sẽ load dần (lazy loading). Scroll xuống để trigger loading.

---

## 📊 Performance Tips

### Để Tăng Tốc Độ Query:

1. **Giảm top_k**: 50 → 30 (ít results hơn, nhanh hơn)
2. **Giảm số steps**: 5 → 3 (ít queries hơn, nhanh hơn)
3. **Cache hit**: Query lại cùng text = 0.02s (instant!)

### Để Tăng Accuracy:

1. **Tắt "Require all steps"**: Cho phép partial matches
2. **Tăng top_k**: 50 → 100 (nhiều options hơn)
3. **Dùng descriptive queries**: "red car" thay vì "car"

---

## 🎯 Workflow Cho DRES Competition

### Khi Nhận Được Câu Hỏi:

1. **Đọc kỹ câu hỏi** → xác định temporal sequence
2. **Chia thành 3-5 steps** → mỗi step là 1 scene/event
3. **Mở frontend** → Enable multi-step mode
4. **Nhập từng step** → dùng keywords, không cần full sentence
5. **Set top_k = 50** → balance giữa speed và coverage
6. **Tắt "Require all steps"** → maximum recall
7. **Click search** → chờ 1-2 giây
8. **Scan top 10 results** → ưu tiên green borders
9. **Click vào result** → xem video preview
10. **Submit khi chắc chắn**

### Ví Dụ Thực Tế:

**DRES Question**: "Find video about news reporter discussing scams, then shows aerial mountain views, then girls taking selfies"

**Your Action**:
```
Step 1: news reporter scams
Step 2: aerial mountain view
Step 3: girls taking selfies
Top-K: 50
Require all: OFF
```

**Result**: 50 results in 1.2s, top 3 có green border (100% match)

---

## 📞 Quick Commands Reference

### Trên Server (qua SSH):

```bash
# Check system status
bash /home/ir/check_system.sh

# Start system (if stopped)
bash /home/ir/start_system.sh

# Stop backend
pkill -f 'python.*main.py'

# Stop frontend
pkill -f 'http.server.*8007'

# Restart backend
cd /home/ir/retrievalBaseline/backend
pkill -f 'python.*main.py'
nohup python3 main.py > backend.log 2>&1 &

# View logs
tail -50 /home/ir/retrievalBaseline/backend/backend.log

# Test system
python3 /home/ir/test_frontend_backend_integration.py
```

### Trên Windows (PowerShell):

```powershell
# Create SSH tunnel
ssh -L 18007:localhost:8007 -L 18000:localhost:8000 ir@192.168.28.32

# Test backend (trong browser hoặc PowerShell)
curl http://localhost:18000/health

# Test frontend
curl http://localhost:18007
```

---

## ✅ Final Checklist

Trước khi dùng cho competition:

- [ ] SSH tunnel đã tạo và đang mở
- [ ] Browser mở được `http://localhost:18007`
- [ ] Backend health OK: `http://localhost:18000/health`
- [ ] Toggle "Multi-Step Query Mode" hiển thị
- [ ] Test query đơn giản hoạt động
- [ ] Images load được (có thể hơi chậm lần đầu)
- [ ] Step badges hiển thị trên results

**Nếu tất cả OK → Sẵn sàng cho competition! 🏆**

---

## 🆘 Need Help?

### Test Nhanh:
```bash
python3 /home/ir/test_frontend_backend_integration.py
```

### Check Logs:
```bash
# Backend
tail -100 /home/ir/retrievalBaseline/backend/backend_sequential.log

# Frontend
tail -100 /home/ir/retrievalBaseline/frontend/frontend.log
```

### Contact Info:
- Server IP: `192.168.28.32`
- Username: `ir`
- Backend: Port 8000
- Frontend: Port 8007

**Good luck with the competition! 🚀**
