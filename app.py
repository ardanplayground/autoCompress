import streamlit as st
from PIL import Image
import io

# Konfigurasi halaman
st.set_page_config(
    page_title="AutoCompress Image",
    page_icon="🖼️",
    layout="wide"
)

st.title("🖼️ AutoCompress Image")
st.markdown("Upload gambar JPG, JPEG, PNG untuk dikompresi otomatis!")

# Fungsi untuk format ukuran file
def format_file_size(size_bytes):
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} bytes"

# Fungsi compress gambar
def compress_image(image, output_format, quality=85):
    output = io.BytesIO()
    
    if output_format.upper() in ['JPG', 'JPEG']:
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        image.save(output, format='JPEG', quality=quality, optimize=True)
    elif output_format.upper() == 'PNG':
        image.save(output, format='PNG', optimize=True)
    
    return output.getvalue()

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Pengaturan")
    
    output_format = st.selectbox(
        "Format Output",
        ["JPEG", "PNG"]
    )
    
    quality = st.slider(
        "Kualitas Kompresi",
        min_value=10,
        max_value=95,
        value=85
    )
    
    st.info("💡 Kualitas lebih rendah = ukuran file lebih kecil")

# File uploader
uploaded_files = st.file_uploader(
    "📁 Drag & drop gambar di sini (JPG, JPEG, PNG)",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} gambar siap diproses!")
    
    total_original = 0
    total_compressed = 0
    
    for i, file in enumerate(uploaded_files):
        st.write(f"---")
        st.subheader(f"📄 {file.name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(file, caption="Gambar Asli", use_column_width=True)
            
        with col2:
            with st.spinner("Memproses..."):
                try:
                    # Baca gambar
                    image = Image.open(io.BytesIO(file.getvalue()))
                    
                    # Compress gambar
                    compressed_data = compress_image(image, output_format, quality)
                    
                    # Hitung ukuran
                    original_size = len(file.getvalue())
                    compressed_size = len(compressed_data)
                    reduction = ((original_size - compressed_size) / original_size) * 100
                    
                    # Tampilkan hasil
                    st.image(compressed_data, caption="Hasil Kompresi", use_column_width=True)
                    
                    st.info(f"""
                    **📊 Hasil Kompresi:**
                    - Asli: {format_file_size(original_size)}
                    - Hasil: {format_file_size(compressed_size)}
                    - Pengurangan: **{reduction:.1f}%**
                    """)
                    
                    # Download button
                    ext = "jpg" if output_format.upper() in ['JPG', 'JPEG'] else "png"
                    st.download_button(
                        label=f"📥 Download Gambar",
                        data=compressed_data,
                        file_name=f"compressed_{file.name.split('.')[0]}.{ext}",
                        mime=f"image/{ext}",
                        key=f"dl_{i}"
                    )
                    
                    total_original += original_size
                    total_compressed += compressed_size
                    
                except Exception as e:
                    st.error(f"❌ Gagal memproses {file.name}: {str(e)}")
    
    # Total summary
    if total_original > 0:
        total_reduction = ((total_original - total_compressed) / total_original) * 100
        st.success(f"""
        **🎉 Ringkasan Total:**
        - Total Ukuran Asli: {format_file_size(total_original)}
        - Total Ukuran Hasil: {format_file_size(total_compressed)}  
        - Total Penghematan: **{total_reduction:.1f}%**
        - File Diproses: {len(uploaded_files)}
        """)

else:
    st.info("""
    **📖 Cara Penggunaan:**
    1. Upload gambar JPG/JPEG/PNG
    2. Atur pengaturan kompresi di sidebar
    3. Download hasil kompresi
    
    **✨ Fitur:**
    - ✅ Multiple file upload
    - ✅ Kompresi otomatis
    - ✅ Tidak disimpan di server
    - ✅ Download hasil
    - ✅ Ringkasan penghematan
    """)

# Footer
st.markdown("---")
st.caption("🛡️ File Anda aman - tidak disimpan di server setelah diproses")
