import os
import json
import click
import hashlib
from datetime import datetime
from rich.console import Console
from rich.table import Table

from utils.api_client import make_request
from utils.blockchain.fabric import FabricConnector, BlockchainDocument

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

from .permissions import permissions
from .metadata import metadata
from .graph import graph


console = Console()


def compress_data(data: bytes) -> bytes:
    """Compress data using zstd compression."""
    if not ZSTD_AVAILABLE:
        raise RuntimeError("zstandard library is not available")
    
    compressor = zstd.ZstdCompressor(level=1)  # Use level 1 for fast compression
    return compressor.compress(data)


def decompress_data(data: bytes) -> bytes:
    """Decompress data using zstd decompression."""
    if not ZSTD_AVAILABLE:
        raise RuntimeError("zstandard library is not available")
    
    decompressor = zstd.ZstdDecompressor()
    return decompressor.decompress(data)


def decompress_data_streaming(data: bytes) -> bytes:
    """Decompress data using zstd streaming decompression (more robust)."""
    if not ZSTD_AVAILABLE:
        raise RuntimeError("zstandard library is not available")
    
    decompressor = zstd.ZstdDecompressor()
    
    # Try streaming decompression first (more robust)
    try:
        from io import BytesIO
        input_stream = BytesIO(data)
        output_stream = BytesIO()
        
        decompressor.copy_stream(input_stream, output_stream)
        return output_stream.getvalue()
    except Exception:
        # Fallback to regular decompression
        return decompressor.decompress(data)


@click.group()
def documents():
    """Create, download, and manage provenance documents."""
    pass


@documents.command(name="list")
@click.option('--page', default=0, show_default=True, type=int, help="Page number (zero-indexed).")
@click.option('--page-size', default=10, show_default=True, type=int, help="Number of documents per page.")
@click.option('--updated-after', type=str, help="List only documents updated after this ISO 8601 datetime (e.g., '2024-06-01T00:00:00Z').")
@click.option('--created-after', type=str, help="List only documents created after this ISO 8601 datetime (e.g., '2024-06-01T00:00:00Z').")
@click.pass_context
def list_documents(ctx, page, page_size, updated_after, created_after):
    """List all available document records, with pagination and optional updated-after filter."""
    api_url = ctx.obj['API_URL']
    params = {'page': page, 'page_size': page_size}
    if updated_after:
        params['updated_after'] = updated_after
    if created_after:
        params['created_after'] = created_after
    response = make_request("GET", api_url, "/documents", params=params)

    if response and response.status_code == 200:
        doc_list = response.json()
        if not doc_list:
            console.print("[yellow]No documents found.[/yellow]")
            return

        table = Table(title=f"Available Provenance Documents (Page {page}, Size {page_size})")
        table.add_column("PID", style="cyan", no_wrap=True)
        table.add_column("Version", style="magenta")
        table.add_column("Owner", style="green")
        table.add_column("Parent PID", style="cyan")

        for doc in doc_list:
            table.add_row(doc['pid'], str(doc['version']), doc['owner_email'], doc.get('parent_document_pid', 'N/A'))

        console.print(table)
    else:
        console.print(f"❌ [bold red]Error[/bold red] {response.status_code if response else ''}: {response.text if response else 'No response.'}")


@documents.command(name="get")
@click.argument('pid')
@click.pass_context
def get_document(ctx, pid):
    """Get detailed info for a specific document by its PID."""
    api_url = ctx.obj['API_URL']
    response = make_request("GET", api_url, f"/documents/{pid}")

    if response and response.status_code == 200:
        console.print_json(data=response.json())


@documents.command(name="create")
@click.option(
    '--json-file',
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to a JSON file with the document data."
)
@click.option(
    '-v', '--value',
    help="A JSON string containing the document data."
)
@click.option(
    '--parent-pid',
    help="PID of the parent document, if any."
)
@click.option(
    '--trustworthy',
    is_flag=True,
    help="Also create a record of the document on the blockchain for enhanced trustworthiness."
)
@click.option(
    '--compressed',
    is_flag=True,
    help="Compress the document data using zstd before uploading to reduce transfer size."
)
@click.pass_context
def create_document(ctx, json_file, value, parent_pid, trustworthy, compressed):
    """Publish a new document, from a JSON file or a JSON string."""
    # Enforce exactly one input source
    if bool(json_file) == bool(value):
        console.print("❌ [bold red]Error:[/bold red] You must provide exactly one of --json-file or --value.")
        return

    # Check if compression is requested but zstd is not available
    if compressed and not ZSTD_AVAILABLE:
        console.print("❌ [bold red]Error:[/bold red] Compression requested but zstandard library is not installed.")
        console.print("   Install it with: [cyan]pip install zstandard[/cyan]")
        return

    api_url = ctx.obj['API_URL']
    params = {'parent_document_pid': parent_pid} if parent_pid else {}

    # Validate blockchain required variables beforehand if --trustworthy is set
    if trustworthy:
        try:
            fabric_connector = FabricConnector()
            fabric_connector.get_env_vars()
        except RuntimeError as e:
            console.print(f"❌ [bold red]Error:[/bold red] {e}")
            return

    # Load document_data from file or string
    try:
        headers = {}
        if compressed:
            headers["Content-Encoding"] = "zstd"
            console.print("🗜️ [blue]Compressing document data with zstd...[/blue]")

        if json_file:
            if compressed:
                # For compressed file upload, read the file, compress it, and send as bytes
                console.print(f"Uploading compressed document from JSON file: [cyan]{json_file}[/cyan]")
                with open(json_file, 'rb') as f:
                    file_data = f.read()
                
                compressed_data = compress_data(file_data)
                console.print(f"[dim]Original size: {len(file_data)} bytes, Compressed size: {len(compressed_data)} bytes ({len(compressed_data)/len(file_data)*100:.1f}%)[/dim]")
                
                # Create a file-like object from compressed data
                from io import BytesIO
                compressed_file = BytesIO(compressed_data)
                files = {
                    'document_file': (os.path.basename(json_file), compressed_file, 'application/json')
                }
                response = make_request("POST", api_url, "/documents", params=params, files=files, headers=headers)
            else:
                # Stream-upload the JSON file as multipart/form-data so we don't load it into memory.
                console.print(f"Uploading document from JSON file (streamed): [cyan]{json_file}[/cyan]")
                # Open file and pass file object to make_request via 'files' so requests streams from disk.
                # The backend should accept the form field 'document_file' containing the JSON file.
                with open(json_file, 'rb') as f:
                    files = {
                        'document_file': (os.path.basename(json_file), f, 'application/json')
                    }
                    # No JSON body in this case; use multipart file upload.
                    response = make_request("POST", api_url, "/documents", params=params, files=files)
        else:
            document_data = json.loads(value)
            
            if compressed:
                console.print("Uploading compressed document from JSON string.")
                # Convert to JSON bytes and compress
                json_bytes = json.dumps(document_data).encode('utf-8')
                compressed_data = compress_data(json_bytes)
                console.print(f"[dim]Original size: {len(json_bytes)} bytes, Compressed size: {len(compressed_data)} bytes ({len(compressed_data)/len(json_bytes)*100:.1f}%)[/dim]")
                
                # Send compressed data as file upload with Content-Encoding header
                from io import BytesIO
                compressed_file = BytesIO(compressed_data)
                files = {
                    'document_file': ('document.json', compressed_file, 'application/json')
                }
                response = make_request("POST", api_url, "/documents", params=params, files=files, headers=headers)
            else:
                console.print("Uploading document from JSON string.")
                # Make the API request with JSON payload for the string case.
                payload = {"document_data": document_data}
                response = make_request("POST", api_url, "/documents", params=params, json=payload)
    except json.JSONDecodeError as e:
        console.print(f"❌ [bold red]Error:[/bold red] Invalid JSON provided: {e}")
        return
    except IOError as e:
        console.print(f"❌ [bold red]Error:[/bold red] Cannot read file '{json_file}': {e}")
        return

    # Handle response (same as before)
    if response and response.status_code == 200:
        console.print("✅ [bold green]Document created successfully![/bold green]")
        response_data = response.json()
        console.print_json(data=response_data)
        
        # If --trustworthy flag is set, also create blockchain record
        if trustworthy:
            console.print("\n📝 Creating blockchain record for enhanced trustworthiness...")
            try:
                # Extract document info from API response
                doc_info = response_data.get('document_record', response_data)
                pid = doc_info.get('pid')
                document_hash = doc_info.get('hash')  # Assuming the API returns the document hash
                owner_email = doc_info.get('owner_email')
                
                if not pid:
                    console.print("❌ [bold red]Error:[/bold red] Could not extract PID from API response.")
                    return
                
                if not document_hash:
                    console.print("❌ [bold yellow]Warning:[/bold yellow] No document hash found in API response. Using placeholder.")
                    document_hash = "placeholder_hash_" + datetime.now().strftime('%Y%m%d%H%M%S')
                
                if not owner_email:
                    console.print("❌ [bold yellow]Warning:[/bold yellow] No owner email found in API response. Using placeholder.")
                    owner_email = "unknown_owner"
                
                # Construct document URL (assuming the API provides a way to access the document)
                api_url = ctx.obj['API_URL']
                document_url = f"{api_url}/documents/{pid}/download"
                
                # Create blockchain document
                blockchain_doc = BlockchainDocument(
                    pid=pid,
                    url=document_url,
                    hash=document_hash,
                    timestamp=datetime.now().isoformat(),
                    owners=[owner_email]
                )
                console.print(f"[blue]Storing document record to blockchain:\n{json.dumps(blockchain_doc.__dict__, indent=2)}[/blue]")
                
                # Connect to blockchain and create document
                connector = FabricConnector()
                blockchain_result = connector.create_document(blockchain_doc)
                
                console.print("✅ [bold green]Document record created successfully on blockchain![/bold green]")
                console.print(f"Blockchain transaction:\n[dim]{blockchain_result}[/dim]")

            except Exception as e:
                console.print("❌ [bold red]Error creating blockchain record:[/bold red]")
                console.print(f"   {str(e)}")
                console.print("   [dim]Document was still created successfully on the API server.[/dim]")
    else:
        console.print(f"❌ [bold red]Error[/bold red] {response.status_code if response else ''}: {response.text if response else 'No response.'}")


@documents.command(name="download")
@click.argument('pid')
@click.option(
    '-o', '--output',
    type=click.Path(dir_okay=False, writable=True),
    help="Full path to save the file (e.g., 'my_dir/my_doc.json'). This overrides --output-folder."
)
@click.option(
    '--output-folder',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
    help="Folder to save the file in. The filename will default to the document's PID."
)
@click.option(
    '--trustworthy/--no-trustworthy',
    default=False,
    help="Verify SHA256: compare local file hash with yProvStore and blockchain values."
)
@click.option(
    '--compressed',
    is_flag=True,
    help="Request compressed download from server to reduce transfer size (requires zstd)."
)
@click.option(
    '--debug',
    is_flag=True,
    help="Enable debug output for troubleshooting compression issues."
)
@click.pass_context
def download_document(ctx, pid, output, output_folder, trustworthy, compressed, debug):
    """Download a document file by its PID. Optionally verify its SHA256 hash."""
    # Check if compression is requested but zstd is not available
    if compressed and not ZSTD_AVAILABLE:
        console.print("❌ [bold red]Error:[/bold red] Compressed download requested but zstandard library is not installed.")
        console.print("   Install it with: [cyan]pip install zstandard[/cyan]")
        return

    api_url = ctx.obj['API_URL']

    # Determine base folder + final output path
    if output:
        output_path = output
        output_folder = os.path.dirname(output_path) or os.getcwd()
    else:
        base_folder = output_folder or os.getcwd()
        split = pid.split('/')
        if len(split) == 2:
            prefix, doc_id = split
            prefix_path = os.path.join(base_folder, prefix)
            os.makedirs(prefix_path, exist_ok=True)
            output_path = os.path.join(prefix_path, f"{doc_id}.json")
        elif len(split) > 2:
            console.print(f"❌ [bold red]Error:[/bold red] Invalid PID format '{pid}'. Expected format is 'prefix/pid' or 'pid'.")
            return
        else:
            # single-part PID
            output_path = os.path.join(base_folder, f"{pid}.json")

    if compressed:
        console.print(f"Downloading document [cyan]{pid}[/cyan] (compressed) to [yellow]{output_path}[/yellow]...")
    else:
        console.print(f"Downloading document [cyan]{pid}[/cyan] to [yellow]{output_path}[/yellow]...")

    # Set up headers for compressed download if requested
    headers = {}
    if compressed:
        headers["Accept-Encoding"] = "zstd"

    # perform the download (streaming)
    response = make_request("GET", api_url, f"/documents/{pid}/download", stream=True, headers=headers)
    if not response:
        console.print(f"❌ [bold red]Error:[/bold red] No response from server while downloading '{pid}'.")
        return

    if debug:
        console.print(f"[dim]Response status: {response.status_code}[/dim]")
        console.print(f"[dim]Response headers: {dict(response.headers)}[/dim]")

    if response.status_code != 200:
        console.print(f"❌ [bold red]Error:[/bold red] Failed to download document ({response.status_code}).")
        try:
            # show server message if present
            console.print(response.text)
        except Exception:
            pass
        return

    try:
        # Check if the response is compressed
        is_compressed = response.headers.get('Content-Encoding') == 'zstd'
        
        if debug:
            console.print(f"[dim]Content-Encoding header: {response.headers.get('Content-Encoding', 'None')}[/dim]")
            console.print(f"[dim]Is compressed: {is_compressed}[/dim]")
            console.print(f"[dim]Requested compression: {compressed}[/dim]")
        
        if compressed and is_compressed:
            console.print("🗜️ [blue]Receiving compressed data, decompressing...[/blue]")
            # For compressed responses, we need to collect all data first, then decompress
            compressed_data = b''
            original_size = 0
            # Read raw response stream to get compressed bytes
            for chunk in response.raw.stream(1024, decode_content=False):
                if chunk:
                    compressed_data += chunk
                    original_size += len(chunk)
            
            console.print(f"[dim]Received {original_size} bytes of compressed data[/dim]")
            
            # Check if we actually received zstd data by looking at the magic header
            if len(compressed_data) >= 4:
                magic_header = compressed_data[:4]
                expected_zstd_magic = b'\x28\xb5\x2f\xfd'
                
                if debug:
                    console.print(f"[dim]Data header: {magic_header.hex()}, Expected zstd magic: {expected_zstd_magic.hex()}[/dim]")
                    console.print(f"[dim]First 16 bytes: {compressed_data[:16].hex()}[/dim]")
                
                if magic_header != expected_zstd_magic:
                    console.print(f"[bold yellow]Warning:[/bold yellow] Data doesn't appear to be zstd compressed (wrong magic header)")
                    console.print(f"[yellow]Saving data as-is without decompression...[/yellow]")
                    # Save the data without decompression
                    with open(output_path, 'wb') as f:
                        f.write(compressed_data)
                    console.print(f"✅ [bold green]Download complete![/bold green] File saved to [yellow]{output_path}[/yellow].")
                    return
            else:
                console.print(f"[bold red]Error:[/bold red] Received data is too small ({len(compressed_data)} bytes) to be valid zstd")
                return
            
            # Decompress the data
            try:
                decompressed_data = decompress_data_streaming(compressed_data)
                console.print(f"[dim]Compressed size: {original_size} bytes, Decompressed size: {len(decompressed_data)} bytes (saved {(1-original_size/len(decompressed_data))*100:.1f}% bandwidth)[/dim]")
                
                # Write decompressed data to file
                with open(output_path, 'wb') as f:
                    f.write(decompressed_data)
            except Exception as e:
                console.print(f"[bold red]Error decompressing data:[/bold red] {e}")
                console.print(f"[yellow]Attempting to save raw data without decompression...[/yellow]")
                try:
                    with open(output_path, 'wb') as f:
                        f.write(compressed_data)
                    console.print(f"[yellow]Raw data saved to [cyan]{output_path}[/cyan]. You may need to decompress it manually.[/yellow]")
                except Exception as save_error:
                    console.print(f"[bold red]Error saving raw data:[/bold red] {save_error}")
                return
        else:
            # Regular streaming download
            if compressed and not is_compressed:
                console.print("[yellow]Server did not return compressed data, downloading normally...[/yellow]")
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        
        console.print(f"✅ [bold green]Download complete![/bold green] File saved to [yellow]{output_path}[/yellow].")
    except IOError as e:
        console.print(f"[bold red]Error writing to file:[/bold red] {e}")
        return

    # If trustworthy verification requested, recompute and compare hashes
    if trustworthy:
        console.print("🔎 Verifying document trustworthiness (local SHA256 vs yProvStore vs blockchain)...")

        # helper to compute sha256 of file (streaming)
        def compute_sha256(path):
            h = hashlib.sha256()
            try:
                with open(path, 'rb') as fh:
                    for chunk in iter(lambda: fh.read(8192), b''):
                        h.update(chunk)
                return h.hexdigest()
            except Exception as e:
                console.print(f"[bold red]Error computing SHA256 of local file:[/bold red] {e}")
                return None

        local_hash = compute_sha256(output_path)
        if not local_hash:
            console.print("[bold red]Failed to compute local hash; aborting verification.[/bold red]")
            return

        # 1) Get DB hash from API /documents/{pid}
        db_hash = None
        response_meta = make_request("GET", api_url, f"/documents/{pid}")
        if response_meta and response_meta.status_code == 200:
            try:
                meta = response_meta.json()
                # look for common hash keys
                db_hash = meta.get('sha256') or meta.get('hash') or meta.get('documentHash') or meta.get('document_hash')
            except Exception as e:
                console.print(f"[bold yellow]Warning:[/bold yellow] Could not parse JSON from metadata response: {e}")
        else:
            console.print(f"[bold yellow]Warning:[/bold yellow] Can't fetch document metadata from API (status: {getattr(response_meta, 'status_code', 'no response')}).")

        # 2) Get blockchain hash via FabricConnector
        bc_hash = None
        try:
            connector = FabricConnector()
            bc_raw = connector.read_document(pid)
            # bc_raw may be JSON string or already a dict-like; try to convert safely
            if isinstance(bc_raw, str):
                try:
                    bc_json = json.loads(bc_raw)
                except json.JSONDecodeError:
                    # if it's just a raw hash string, treat it as such
                    bc_json = {'hash': bc_raw}
            else:
                bc_json = bc_raw

            # extract possible keys
            if isinstance(bc_json, dict):
                bc_hash = bc_json.get('hash')
            else:
                console.print(f"[bold yellow]Warning:[/bold yellow] Unexpected blockchain document format {type(bc_json)}:\n[dim]{bc_json}[/dim]")
        except Exception as e:
            console.print(f"[bold yellow]Warning:[/bold yellow] Blockchain read failed: {e}")

        # Print and compare results
        console.print("\nHashes:")
        console.print(f" • Local:      [cyan]{local_hash}[/cyan]")
        console.print(f" • yProvStore: [cyan]{db_hash or 'N/A'}[/cyan]")
        console.print(f" • Blockchain: [cyan]{bc_hash or 'N/A'}[/cyan]\n")

        ok_db = (db_hash is not None and local_hash == db_hash)
        ok_bc = (bc_hash is not None and local_hash == bc_hash)

        if ok_db and ok_bc:
            console.print("✅ [bold green]All checks passed:[/bold green] local hash matches yProvStore and blockchain.")
        else:
            if not db_hash:
                console.print("❌ [bold red]yProvStore hash unavailable or could not be read.[/bold red]")
            elif not ok_db:
                console.print("❌ [bold red]Mismatch:[/bold red] local hash does not match yProvStore hash.")
            if not bc_hash:
                console.print("❌ [bold red]Blockchain hash unavailable or could not be read.[/bold red]")
            elif not ok_bc:
                console.print("❌ [bold red]Mismatch:[/bold red] local hash does not match blockchain hash.")


documents.add_command(permissions)
documents.add_command(metadata)
documents.add_command(graph)
