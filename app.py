import streamlit as st
import io
import os
from PIL import Image
import base64
import fitz  # PyMuPDF

# Konfigurasi halaman
st.set_page_config(
    page_title="AutoCompress - PDF & Image Compressor",
    page_icon="🗜️",
    layout="wide"
)

# CSS Custom
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

def get_file_size_str(size_bytes):
    """Konversi ukuran file ke format yang mudah dibaca"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def compress_image(image_file, quality=85, max_size_kb=None, max_size_mb=None):
    """Kompresi gambar dengan opsi quality dan ukuran maksimal"""
    try:
        # Baca gambar
        image = Image.open(image_file)
        
        # Konversi RGBA ke RGB jika perlu
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        
        # Hitung target size jika ada
        target_size = None
        if max_size_kb:
            target_size = max_size_kb * 1024
        elif max_size_mb:
            target_size = max_size_mb * 1024 * 1024
        
        # Kompresi dengan quality yang ditentukan
        output = io.BytesIO()
        current_quality = quality
        
        # Jika ada target size, coba kompresi hingga mencapai target
        if target_size:
            while current_quality > 10:
                output = io.BytesIO()
                
                # Resize jika perlu untuk mencapai target size
                temp_image = image.copy()
                temp_image.save(output, format='JPEG', quality=current_quality, optimize=True)
                
                if output.tell() <= target_size or current_quality <= 15:
                    break
                    
                current_quality -= 5
                
                # Jika quality sudah rendah tapi masih terlalu besar, resize gambar
                if current_quality <= 20 and output.tell() > target_size:
                    scale = 0.9
                    new_size = (int(temp_image.width * scale), int(temp_image.height * scale))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
        else:
            image.save(output, format='JPEG', quality=current_quality, optimize=True)
        
        output.seek(0)
        return output, current_quality
        
    except Exception as e:
        st.error(f"Error saat kompresi gambar: {str(e)}")
        return None, None

def compress_pdf(pdf_file, max_size_kb=None, max_size_mb=None):
    """Kompresi PDF menggunakan PyMuPDF"""
    try:
        # Baca PDF dari bytes
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)  # Reset pointer
        
        # Buka PDF document
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Hitung target size jika ada
        target_size = None
        if max_size_kb:
            target_size = max_size_kb * 1024
        elif max_size_mb:
            target_size = max_size_mb * 1024 * 1024
        
        # Tentukan DPI berdasarkan target size
        dpi = 150  # Default DPI
        if target_size:
            # Kurangi DPI jika target size kecil
            original_size = len(pdf_bytes)
            if target_size < original_size * 0.3:
                dpi = 100
            elif target_size < original_size * 0.5:
                dpi = 120
        
        # Buat PDF baru dengan kompresi
        output_pdf = fitz.open()
        
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            
            # Render halaman ke gambar dengan DPI yang ditentukan
            zoom = dpi / 72  # 72 adalah DPI default
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Konversi ke PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Tentukan quality berdasarkan target size
            quality = 85
            if target_size:
                target_per_page = target_size / pdf_document.page_count
                # Coba beberapa quality level
                for q in [85, 75, 65, 55, 45, 35]:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='JPEG', quality=q, optimize=True)
                    if img_bytes.tell() <= target_per_page:
                        quality = q
                        break
            
            # Simpan gambar dengan quality yang sudah ditentukan
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=quality, optimize=True)
            img_bytes.seek(0)
            
            # Buat PDF page dari gambar
            img_pdf = fitz.open(stream=img_bytes.read(), filetype="jpeg")
            page_rect = page.rect
            pdf_page = output_pdf.new_page(width=page_rect.width, height=page_rect.height)
            pdf_page.insert_image(page_rect, stream=img_bytes.getvalue())
            img_pdf.close()
        
        # Simpan ke output dengan kompresi maksimal
        output = io.BytesIO()
        output_pdf.save(output, garbage=4, deflate=True, clean=True)
        output_pdf.close()
        pdf_document.close()
        
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"Error saat kompresi PDF: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def create_download_link(file_bytes, filename, file_type):
    """Buat link download untuk file yang sudah dikompresi"""
    b64 = base64.b64encode(file_bytes.read()).decode()
    file_bytes.seek(0)
    
    if file_type == "image":
        mime = "image/jpeg"
    else:
        mime = "application/pdf"
    
    href = f'<a href="data:{mime};base64,{b64}" download="{filename}" style="text-decoration:none;"><button style="background-color:#4CAF50;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;">📥 Download File Terkompresi</button></a>'
    return href

# Header
st.markdown('<div class="main-header">🗜️ AutoCompress</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Kompresi PDF & Gambar dengan Mudah dan Aman</div>', unsafe_allow_html=True)

# Info keamanan
with st.expander("ℹ️ Tentang Keamanan File"):
    st.info("""
    **Keamanan File Terjamin:**
    - File diproses sementara di server dan langsung dihapus setelah kompresi
    - Tidak ada file yang disimpan permanen
    - Setiap sesi pengguna terisolasi
    - Proses kompresi dilakukan secara lokal pada session Anda
    """)

# Sidebar untuk pengaturan
st.sidebar.header("⚙️ Pengaturan Kompresi")

file_type = st.sidebar.selectbox(
    "Pilih Tipe File:",
    ["Gambar (JPG, PNG)", "PDF"]
)

# Advanced Options
with st.sidebar.expander("🔧 Advanced Options", expanded=False):
    st.markdown("**Batasan Ukuran File (Opsional)**")
    st.caption("Kosongkan jika tidak perlu batasan ukuran tertentu")
    
    col1, col2 = st.columns(2)
    with col1:
        use_kb = st.checkbox("Gunakan KB")
        if use_kb:
            max_kb = st.number_input("Maksimal (KB)", min_value=10, max_value=10000, value=500, step=10)
        else:
            max_kb = None
    
    with col2:
        use_mb = st.checkbox("Gunakan MB")
        if use_mb:
            max_mb = st.number_input("Maksimal (MB)", min_value=0.1, max_value=100.0, value=1.0, step=0.1)
        else:
            max_mb = None
    
    if use_kb and use_mb:
        st.warning("⚠️ Pilih salah satu: KB atau MB")
    
    if file_type == "Gambar (JPG, PNG)":
        st.markdown("**Kualitas Kompresi Gambar**")
        quality = st.slider("Quality (%)", min_value=10, max_value=100, value=85, step=5)
        st.caption("Quality lebih rendah = ukuran file lebih kecil")

# Area upload
st.markdown("### 📤 Upload File")

if file_type == "Gambar (JPG, PNG)":
    uploaded_file = st.file_uploader(
        "Pilih gambar untuk dikompresi",
        type=['jpg', 'jpeg', 'png'],
        help="Format yang didukung: JPG, JPEG, PNG"
    )
else:
    uploaded_file = st.file_uploader(
        "Pilih PDF untuk dikompresi",
        type=['pdf'],
        help="Format yang didukung: PDF"
    )

# Proses kompresi
if uploaded_file is not None:
    # Tampilkan info file original
    original_size = len(uploaded_file.getvalue())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Nama File", uploaded_file.name)
    with col2:
        st.metric("📊 Ukuran Original", get_file_size_str(original_size))
    with col3:
        st.metric("📋 Tipe", uploaded_file.type)
    
    # Tombol compress
    if st.button("🗜️ COMPRESS NOW", type="primary"):
        with st.spinner("Sedang memproses... Mohon tunggu"):
            
            # Reset pointer file
            uploaded_file.seek(0)
            
            if file_type == "Gambar (JPG, PNG)":
                # Validasi checkbox
                if use_kb and use_mb:
                    st.error("❌ Silakan pilih hanya satu: KB atau MB di Advanced Options")
                else:
                    compressed_file, final_quality = compress_image(
                        uploaded_file,
                        quality=quality if not (use_kb or use_mb) else 85,
                        max_size_kb=max_kb if use_kb else None,
                        max_size_mb=max_mb if use_mb else None
                    )
                    
                    if compressed_file:
                        compressed_size = len(compressed_file.getvalue())
                        compression_ratio = ((original_size - compressed_size) / original_size) * 100
                        
                        # Tampilkan hasil
                        st.markdown('<div class="success-box">', unsafe_allow_html=True)
                        st.success("✅ Kompresi Berhasil!")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📉 Ukuran Setelah Kompresi", get_file_size_str(compressed_size))
                        with col2:
                            st.metric("💾 Penghematan", f"{compression_ratio:.1f}%")
                        with col3:
                            st.metric("🎯 Quality Akhir", f"{final_quality}%")
                        
                        # Preview gambar
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Original**")
                            uploaded_file.seek(0)
                            st.image(uploaded_file, use_container_width=True)
                        with col2:
                            st.markdown("**Terkompresi**")
                            compressed_file.seek(0)
                            st.image(compressed_file, use_container_width=True)
                        
                        # Link download
                        compressed_file.seek(0)
                        filename = f"compressed_{uploaded_file.name.rsplit('.', 1)[0]}.jpg"
                        st.markdown(create_download_link(compressed_file, filename, "image"), unsafe_allow_html=True)
            
            else:  # PDF
                # Validasi checkbox
                if use_kb and use_mb:
                    st.error("❌ Silakan pilih hanya satu: KB atau MB di Advanced Options")
                else:
                    compressed_file = compress_pdf(
                        uploaded_file,
                        max_size_kb=max_kb if use_kb else None,
                        max_size_mb=max_mb if use_mb else None
                    )
                    
                    if compressed_file:
                        compressed_size = len(compressed_file.getvalue())
                        compression_ratio = ((original_size - compressed_size) / original_size) * 100
                        
                        # Tampilkan hasil
                        st.markdown('<div class="success-box">', unsafe_allow_html=True)
                        st.success("✅ Kompresi Berhasil!")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("📉 Ukuran Setelah Kompresi", get_file_size_str(compressed_size))
                        with col2:
                            st.metric("💾 Penghematan", f"{compression_ratio:.1f}%")
                        
                        # Link download
                        compressed_file.seek(0)
                        filename = f"compressed_{uploaded_file.name}"
                        st.markdown(create_download_link(compressed_file, filename, "pdf"), unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>AutoCompress</strong> - Kompresi file dengan aman dan mudah</p>
    <p style='font-size: 0.9rem;'>File Anda diproses secara aman dan tidak disimpan</p>
    <p style='font-size: 0.9rem;'>Made with 💖 by Ardan</p>
</div>
""", unsafe_allow_html=True)
