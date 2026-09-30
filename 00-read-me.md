# LuxuryAuthRegistryX — Context Priming & Technical Architecture
**Dự Án: LuxuryAuthRegistryX — Autonomous Stolen & Counterfeit Luxury Goods Registry & Dispute Arbiter**

---

## 0. CÁC QUYẾT ĐỊNH CỐT LÕI (GROUND TRUTH)

| # | Hạng mục | Đã chốt | Hệ quả bắt buộc |
|---|---|---|---|
| **D1** | **Mạng triển khai** | **studionet** (GenLayer Studio hosted, `https://studio.genlayer.com`) | Contract deploy trên studionet (Chain ID `61999`). Không nhầm lẫn với testnet. |
| **D2** | **Kênh nộp bài** | **GenLayer Portal — track Builders** (`portal.genlayer.foundation`) | Nộp qua Portal dashboard: GitHub repo + Video demo + Live address. |
| **D3** | **API non-deterministic** | **`gl.vm.run_nondet(leader_fn, validator_fn)`** | So sánh ngữ nghĩa rời rạc (Discrete Consensus Binding): 4 enum chuẩn xác. |

---

## 1. Bản Chất Bài Toán & Định Vị Dự Án

### Vấn Đề Nhức Nhối Của Thị Trường Đồ Hiệu Thứ Cấp
- **Thị trường quy mô khổng lồ nhưng rủi ro cao:** Thị trường thứ cấp cho đồng hồ xa xỉ (Rolex, Patek Philippe, Audemars Piguet), túi hàng hiệu (Hermès Birkin, Chanel) trị giá hàng chục tỷ USD.
- **Vấn nạn hàng trộm cắp và hàng giả:** Khi người mua nhận hàng và phát hiện serial nằm trong danh sách đen/báo mất cảnh sát (The Watch Register, Art Loss Register), các nền tảng escrow truyền thống gặp bế tắc:
  - Cần trọng tài con người mất nhiều tuần/tháng xác minh.
  - Phí thẩm định cao, có nguy cơ thông đồng hoặc thiên vị.
  - Smart contract truyền thống (Solidity) mù thông tin với cơ sở dữ liệu web thời gian thực.

### Giải Pháp GenLayer Fit (Trục 1: Agentic Commerce & Onchain Justice)
`LuxuryAuthRegistryX` giải quyết triệt để vấn đề này bằng cách:
1. **Escrow & Tiền cọc an thực:** Người mua khóa 100% tiền hàng; người bán đặt cọc `seller_bond` cam kết món hàng hợp pháp và chính hãng.
2. **Canonical Host & Serial Binding:** URL tra cứu bắt buộc thuộc danh sách các registry uy tín được cấu hình sẵn trong contract (`thewatchregister.com`, `artloss.com`, `watchregister.org`, v.v.) và URL phải chứa chính xác chuỗi `serial_number` để ngăn chặn hoàn toàn tấn công giả mạo URL / replay.
3. **Thẩm định tự trị qua Web & LLM Consensus:** Khi phát sinh tranh chấp, validator GenLayer truy cập trực tiếp URL tra cứu thông qua `gl.nondet.web.render(lookup_url, mode="text")`.
4. **Hội đồng AI Validator đồng thuận rời rạc (Discrete Consensus):** Đối soát thông tin số serial, đối chiếu biên bản mất cắp/hàng giả.
5. **Giải ngân hoặc tịch thu tự động:**
   - **`STOLEN_FLAGGED` hoặc `COUNTERFEIT_FLAGGED`:** Serial bị đưa vĩnh viễn vào danh sách đen on-chain (`blacklisted_serials`). Tiền escrow được hoàn trả 100% cho người mua, đồng thời toàn bộ tiền cọc của người bán (`seller_bond`) bị tịch thu bồi thường cho người mua.
   - **`AUTHENTIC_CLEAN`:** Giải phóng toàn bộ tiền escrow và trả lại tiền cọc cho người bán.
   - **`INSUFFICIENT_DATA`:** Hoàn trả an toàn tiền cho các bên, không gây thất thoát tài sản.

---

## 2. Kỹ Thuật GenVM Chuẩn Chỉnh & Khắc Phục Lỗi Steward

- **Line 1 Pragma:** `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }` ngay tại dòng đầu tiên tuyệt đối (line 1), không để text/comment nào phía trên.
- **An toàn chuyển tiền:** Không dùng `@gl.evm.contract_interface`, sử dụng cú pháp chuẩn Studio: `gl.get_contract_at(recipient).emit_transfer(value=u256(int(amount)))`.
- **Discrete Consensus Binding (Tránh lỗi unbound/floating point):** Validator khớp chính xác 100% enum trạng thái:
  - `AUTHENTIC_CLEAN`
  - `STOLEN_FLAGGED`
  - `COUNTERFEIT_FLAGGED`
  - `INSUFFICIENT_DATA`
- **Canonical Host & Serial Binding (Tránh URL spoofing / Replay):** Bắt buộc URL tra cứu thuộc các registry hợp lệ được cấu hình sẵn trong contract và URL phải chứa chuỗi số serial tương ứng.
- **An toàn kiểu dữ liệu Storage:** Dùng `bigint`, `TreeMap[str, LuxuryEscrowDeal]`, `TreeMap[str, bool]`, `Address`.
- **Không tái khởi tạo TreeMap trong `__init__`:** Tuân thủ cơ chế auto-initialization của GenVM để tránh lỗi `AssertionError: TreeMap <- TreeMap`.
