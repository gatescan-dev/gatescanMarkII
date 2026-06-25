# glfi_engine/tech_profile.py

class GenericProfile:
    """Knowledge base for Yosys Generic Standard Cells."""
    
    # نگاشت سلول‌های جنریک Yosys به دامنه (Sequential/Combinational) و پین خروجی
    CELL_MAP = {
        # فلیپ‌فلاپ‌ها (خروجی همیشه Q است)
        "$_dff_p_":   {"domain": "SEQ", "out_pin": "Q"},
        "$_dff_n_":   {"domain": "SEQ", "out_pin": "Q"},
        "$_dff_pp0_": {"domain": "SEQ", "out_pin": "Q"},
        "$_dff_pp1_": {"domain": "SEQ", "out_pin": "Q"},
        
        # گیت‌های منطقی پایه (خروجی همیشه Y است)
        "$_and_":     {"domain": "COMB", "out_pin": "Y"},
        "$_or_":      {"domain": "COMB", "out_pin": "Y"},
        "$_xor_":     {"domain": "COMB", "out_pin": "Y"},
        "$_nand_":    {"domain": "COMB", "out_pin": "Y"},
        "$_nor_":     {"domain": "COMB", "out_pin": "Y"},
        "$_xnor_":    {"domain": "COMB", "out_pin": "Y"},
        "$_not_":     {"domain": "COMB", "out_pin": "Y"},
        
        # مالتی‌پلکسر (خروجی Y است)
        "$_mux_":     {"domain": "COMB", "out_pin": "Y"}
    }

    @classmethod
    def get_cell_info(cls, cell_type: str) -> dict:
        """Identifies the cell domain and output pin dynamically based on Yosys types."""
        # پاک‌سازی کاراکترهای اضافی (مثل \ که Yosys گاهی اضافه می‌کند)
        cell_type_lower = cell_type.lower().strip('\\')
        
        for key, val in cls.CELL_MAP.items():
            if cell_type_lower.startswith(key):
                return val
                
        # Heuristic Fallback
        if "dff" in cell_type_lower:
            return {"domain": "SEQ", "out_pin": "Q"}
        
        return {"domain": "COMB", "out_pin": "Y"}