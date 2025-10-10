import streamlit as st
import PIL.Image as Image
import io
import os
import tempfile
from PIL import ImageOps

# Konfigurasi halaman
st.set_page_config(
    page_title="AutoCompress Image",
    page_icon="🖼️",
    layout="wide"
)

# Fungsi untuk mendapatkan ukuran file
def get_file_size(image_bytes):
    return len(image_bytes)

# Fungsi untuk format ukuran file
def format_file_size(size_bytes):
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} bytes"

# Fungsi untuk compress gambar
def compress_image(image, format_type, quality=85, max_size=None, size_unit='KB'):
    """Compress image dengan kualitas optimal atau berdasarkan batas ukuran"""
    
    # Konversi ke RGB jika formatnya JPEG
    if format_type.upper() in ['JPG', 'JPEG'] and image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')
    
    output = io.BytesIO()
    
    if max_size:
        # Compression dengan batas ukuran
        current_quality = quality
        min_quality = 10
        
        for _ in range(10):  # Maksimal 10 iterasi
            output.seek(0)
            output.truncate(0)
            
            if format_type.upper() in ['JPG', 'JPEG']:
                image.save(output, format='JPEG', quality=current_quality, optimize=True)
            elif format_type.upper() == 'PNG':
                image.save(output, format='PNG', optimize=True)
            else:
                image.save(output, format=format_type.upper(), optimize=True)
            
            file_size = len(output.getvalue())
            
            # Konversi ke bytes berdasarkan unit
            if size_unit == 'KB':
                max_size_bytes = max_size * 1024
            else:  # MB
                max_size_bytes = max_size * 1024 * 1024
            
            if file_size <= max_size_bytes or current_quality <= min_quality:
                break
                
            # Kurangi kualitas untuk iterasi berikutnya
            current_quality = max(min_quality, current_quality - 15)
    else:
        # Compression optimal
        if format_type.upper() in ['JPG', 'JPEG']:
            image.save(output, format='JPEG', quality=quality, optimize=True)
        elif format_type.upper() == 'PNG':
            image.save(output, format='PNG', optimize=True)
        else:
            image.save(output, format=format_type.upper(), optimize=True)
    
    return output.getvalue()

# Fungsi untuk handle HEIC dengan pillow-heif
def handle_heic_format(image_data):
    """Handle HEIC format menggunakan pillow-heif"""
    try:
        import pillow_heif
        heif_file = pillow_heif.read_heif(image_data)
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
        )
        return image
    except Exception as e:
        st.error(f"Error membaca file HEIC: {str(e)}")
        return None

# Fungsi untuk memproses gambar
def process_image(uploaded_file, output_format, max_size=None, size_unit='KB'):
    try:
        # Baca gambar
        image_data = uploaded_file.getvalue()
        
        # Handle format HEIC/HEIF
        if uploaded_file.type in ['image/heic', 'image/heif']:
            image = handle_heic_format(image_data)
            if image is None:
                return None, 0, 0, 0
        else:
            # Handle format lainnya
            image = Image.open(io.BytesIO(image_data))
            # Convert ke RGB jika perlu
            if image.mode in ('RGBA', 'P') and output_format.upper() in ['JPG', 'JPEG']:
                image = image.convert('RGB')
        
        # Compress gambar
        compressed_data = compress_image(image, output_format, max_size=max_size, size_unit=size_unit)
        
        # Info gambar asli
        original_size = len(image_data)
        compressed_size = len(compressed_data)
        reduction = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0
        
        return compressed_data, original_size, compressed_size, reduction
        
    except Exception as e:
        st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        return None, 0, 0, 0

# UI Streamlit
st.title("🖼️ AutoCompress Image")
st.markdown("Upload gambar Anda dan secara otomatis akan dikompresi tanpa disimpan di server!")

# Sidebar untuk pengaturan
st.sidebar.header("Pengaturan Kompresi")

# Pilihan format output
output_format = st.sidebar.selectbox(
    "Format Output",
    ["JPEG", "PNG", "WEBP"],
    help="Pilih format output untuk gambar yang dikompresi"
)

# Kualitas default
quality = st.sidebar.slider(
    "Kualitas Kompresi",
    min_value=10,
    max_value=95,
    value=85,
    help="Nilai lebih tinggi = kualitas lebih baik & ukuran file lebih besar"
)

# Opsi ukuran maksimal
use_size_limit = st.sidebar.checkbox("Batasan Ukuran File")

max_size = None
size_unit = 'KB'

if use_size_limit:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        max_size = st.number_input(
            "Ukuran Maksimal",
            min_value=1,
            value=100,
            step=1
        )
    with col2:
        size_unit = st.selectbox("Unit", ["KB", "MB"])

# Area upload
uploaded_files = st.file_uploader(
    "Drag and drop gambar di sini",
    type=['jpg', 'jpeg', 'png', 'heic', 'heif', 'webp', 'bmp', 'tiff'],
    accept_multiple_files=True,
    help="Support format: JPG, JPEG, PNG, HEIC, HEIF, WEBP, BMP, TIFF"
)

if uploaded_files:
    st.subheader(f"📁 {len(uploaded_files)} Gambar Diproses")
    
    total_original_size = 0
    total_compressed_size = 0
    successful_compressions = 0
    
    for i, uploaded_file in enumerate(uploaded_files):
        st.write(f"**{i+1}. {uploaded_file.name}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Tampilkan gambar asli
            try:
                if uploaded_file.type in ['image/heic', 'image/heif']:
                    # Untuk HEIC, konversi dulu ke format yang bisa ditampilkan
                    image = handle_heic_format(uploaded_file.getvalue())
                    if image:
                        st.image(image, caption="Gambar Asli (HEIC)", use_column_width=True)
                    else:
                        st.error("Tidak bisa menampilkan gambar HEIC")
                else:
                    st.image(uploaded_file, caption="Gambar Asli", use_column_width=True)
            except Exception as e:
                st.error(f"Tidak bisa menampilkan gambar: {str(e)}")
        
        with col2:
            with st.spinner(f"Memproses {uploaded_file.name}..."):
                result = process_image(uploaded_file, output_format, max_size, size_unit)
                
                if result[0] is not None:
                    compressed_data, original_size, compressed_size, reduction = result
                    
                    # Tampilkan gambar hasil kompresi
                    try:
                        st.image(compressed_data, caption="Hasil Kompresi", use_column_width=True)
                    except Exception as e:
                        st.error(f"Tidak bisa menampilkan hasil: {str(e)}")
                    
                    # Info ukuran file
                    st.info(f"""
                    **Info Kompresi:**
                    - Ukuran Asli: {format_file_size(original_size)}
                    - Ukuran Hasil: {format_file_size(compressed_size)}
                    - Pengurangan: {reduction:.1f}%
                    """)
                    
                    # Download button
                    file_extension = output_format.lower()
                    if file_extension == 'jpeg':
                        file_extension = 'jpg'
                    
                    st.download_button(
                        label=f"📥 Download {uploaded_file.name.split('.')[0]}_compressed.{file_extension}",
                        data=compressed_data,
                        file_name=f"{uploaded_file.name.split('.')[0]}_compressed.{file_extension}",
                        mime=f"image/{file_extension}",
                        key=f"download_{i}"
                    )
                    
                    total_original_size += original_size
                    total_compressed_size += compressed_size
                    successful_compressions += 1
                else:
                    st.error(f"Gagal memproses {uploaded_file.name}")
        
        st.markdown("---")
    
    # Summary
    if successful_compressions > 0:
        total_reduction = ((total_original_size - total_compressed_size) / total_original_size) * 100 if total_original_size > 0 else 0
        st.success(f"""
        **📊 Ringkasan Total:**
        - Total Ukuran Asli: {format_file_size(total_original_size)}
        - Total Ukuran Hasil: {format_file_size(total_compressed_size)}
        - Total Penghematan: {total_reduction:.1f}%
        - Berhasil Diproses: {successful_compressions}/{len(uploaded_files)} file
        """)

else:
    st.info("👆 Drag and drop gambar Anda di atas untuk memulai kompresi otomatis!")
    
    # Contoh penggunaan
    st.markdown("""
    ### 🚀 Fitur:
    - ✅ Support multiple upload (drag & drop)
    - ✅ Auto delete setelah proses - tidak disimpan di server
    - ✅ Support berbagai format: JPG, JPEG, PNG, HEIC, HEIF, WEBP, BMP, TIFF
    - ✅ Opsi batasan ukuran file (KB/MB)
    - ✅ Kompresi optimal otomatis
    - ✅ Download hasil kompresi
    - ✅ Ringkasan penghematan
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "🛡️ <i>File Anda aman - tidak disimpan di server setelah diproses</i>"
    "</div>",
    unsafe_allow_html=True
)
