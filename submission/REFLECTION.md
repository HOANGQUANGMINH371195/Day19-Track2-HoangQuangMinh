# Reflection — Lab 19

**Tên:** Hoàng Quang Minh
**MSSV:** 2A202601301
**Cohort:** 2A
**Path đã chạy:** docker

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên golden set, BM25 thắng rõ ở nhóm `exact` vì các thuật ngữ kỹ thuật xuất hiện
nguyên văn trong corpus. Vector phù hợp nhất với `paraphrase` vì bắt được ý nghĩa
thay vì chỉ khớp token; nhóm `mixed` hưởng lợi từ cả hai tín hiệu. Hybrid dùng RRF
để giữ kết quả ổn định khi loại query không biết trước, nên là lựa chọn mặc định
cho tìm kiếm tài liệu kỹ thuật. Tuy nhiên tôi không dùng hybrid khi truy vấn luôn
chứa mã lỗi/tên hàm chính xác (BM25 đơn giản và rẻ hơn), hoặc khi corpus đa ngôn
ngữ cần embedding multilingual mà hệ thống hiện tại chưa có. Với câu hỏi thuần
ngữ nghĩa và ngân sách latency rất chặt, pure vector cũng phù hợp hơn.

---

## Điều ngạc nhiên nhất khi làm lab này

Điều đáng chú ý nhất là cùng một công thức RRF có thể cho kết quả khác đáng kể
khi đổi embedding model; chất lượng retrieval phụ thuộc cả model lẫn cách fusion.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- Pair work với: Không
