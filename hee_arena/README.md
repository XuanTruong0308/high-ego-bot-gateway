# 🏆 HEe • Arena — Hệ Thống Tổ Chức Scrims & Giải Đấu eSport

Bot tự động hóa công tác điều phối giải đấu và các buổi Scrims (Liên Minh Huyền Thoại) cho máy chủ High Ego eSport:
- Tự động chia nhánh đấu Knockout (Mì ăn liền) và Vòng bảng -> Chung kết.
- Tự động bốc thăm ngẫu nhiên với `/scrim random`.
- Tự động tạo phòng Voice bảo mật per-team (chỉ cho phép thành viên đội thi đấu kết nối).
- Tự động di chuyển (Move) thành viên vào phòng thi đấu khi giờ đấu bắt đầu.
- Tự động dọn dẹp các phòng voice tạm sau khi trận đấu hoàn tất để tránh rác server.

---

## 🎮 Danh Sách Slash Commands

| Lệnh | Quyền hạn | Mô tả |
|---|---|---|
| `/scrim create [tên_giải] [thể_thức]` | Role `HE` / Admin | Khởi tạo giải đấu mới (Mì ăn liền / Vòng bảng). |
| `/scrim add-team [tên_đội] [đội_trưởng] [tv1]..[tv4]` | Role `HE` / Admin | Đăng ký đội tuyển và tag 5 thành viên chính thức. |
| `/scrim random` | Role `HE` / Admin | Bốc thăm ngẫu nhiên, sinh danh mục và tạo các cặp đấu. |
| `/scrim start-match [mã_trận]` | Role `HE` / Admin | Tạo 2 voice bảo mật riêng, kéo các thành viên vào phòng và ping thông báo. |
| `/scrim result [mã_trận] [đội_thắng]` | Role `HE` / Admin | Cập nhật kết quả và tự động xóa phòng voice của trận. |
| `/scrim bracket` | Mọi thành viên | Xem nhánh đấu, tiến trình hoặc bảng điểm hiện tại. |
| `/scrim cancel` | Role `HE` / Admin | Hủy giải đấu và xóa toàn bộ kênh/category tạm thời. |
