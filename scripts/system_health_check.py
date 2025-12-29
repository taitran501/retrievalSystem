#!/usr/bin/env python3
"""
System Health Check & Diagnostics
Run this to verify all components are working correctly
"""

import sys
import json
import subprocess
from pathlib import Path

def check_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def run_command(cmd, description):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def check_python_dependencies():
    """Check Python packages"""
    check_section("Python Dependencies")
    
    packages = [
        'torch', 'open_clip', 'fastapi', 'uvicorn', 'pymilvus',
        'pillow', 'numpy', 'transformers'
    ]
    
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"✅ {pkg:20s} - Installed")
        except ImportError:
            print(f"❌ {pkg:20s} - Missing")

def check_gpu():
    """Check GPU availability"""
    check_section("GPU Configuration")
    
    try:
        import torch
        print(f"PyTorch version:    {torch.__version__}")
        print(f"CUDA available:     {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA version:       {torch.version.cuda}")
            print(f"GPU device:         {torch.cuda.get_device_name(0)}")
            print(f"GPU memory:         {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            print("\n✅ GPU is available - Backend should use 'device: cuda'")
        else:
            print("\n⚠️  GPU not available - Backend will use CPU (slower)")
    except Exception as e:
        print(f"❌ Error checking GPU: {e}")

def check_milvus():
    """Check Milvus connection"""
    check_section("Milvus Database")
    
    # Check Docker containers
    success, output, _ = run_command("docker ps | grep milvus", "Check Milvus containers")
    
    if success and output:
        print("✅ Milvus containers running:")
        for line in output.split('\n'):
            if 'milvus' in line:
                container_name = line.split()[-1]
                print(f"   - {container_name}")
    else:
        print("❌ Milvus containers not running")
        print("   Start with: cd /home/ir/retrievalBaseline/database && docker-compose up -d")
        return False
    
    # Check Milvus connection
    try:
        from pymilvus import MilvusClient
        client = MilvusClient(uri="http://127.0.0.1:19530", db="default")
        collections = client.list_collections()
        
        print(f"\n✅ Milvus connection successful")
        print(f"   Collections found: {len(collections)}")
        for coll in collections:
            print(f"   - {coll}")
        
        return True
    except Exception as e:
        print(f"❌ Cannot connect to Milvus: {e}")
        return False

def check_backend():
    """Check backend service"""
    check_section("Backend Service")
    
    success, output, _ = run_command("pgrep -f 'python.*main.py'", "Check backend process")
    
    if success and output:
        print(f"✅ Backend process running (PID: {output})")
    else:
        print("❌ Backend process not running")
        print("   Start with: cd /home/ir/retrievalBaseline/backend && nohup python3 main.py > backend.log 2>&1 &")
        return False
    
    # Check backend health endpoint
    success, output, _ = run_command("curl -s http://localhost:8000/health", "Check backend health")
    
    if success and output:
        try:
            health = json.loads(output)
            print(f"\n✅ Backend health check passed:")
            print(f"   Status:              {health.get('status')}")
            print(f"   Models loaded:       {health.get('models_loaded')}")
            print(f"   Database connected:  {health.get('database_connected')}")
            return True
        except:
            print(f"⚠️  Backend responding but health check failed")
            return False
    else:
        print("❌ Backend health endpoint not responding")
        return False

def check_config():
    """Check backend configuration"""
    check_section("Backend Configuration")
    
    config_path = Path("/home/ir/retrievalBaseline/backend/config.json")
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"✅ Config file loaded:")
        print(f"   Model:        {config.get('clip_model_name', 'N/A')}")
        print(f"   Pretrained:   {config.get('clip_pretrained', 'N/A')}")
        print(f"   Device:       {config.get('device', 'N/A')}")
        print(f"   Collection:   {config.get('collection_name', 'N/A')}")
        print(f"   Milvus host:  {config.get('milvus_host', 'N/A')}:{config.get('milvus_port', 'N/A')}")
        
        # Check for issues
        issues = []
        
        if config.get('device') == 'cpu':
            try:
                import torch
                if torch.cuda.is_available():
                    issues.append("⚠️  Device set to 'cpu' but GPU is available")
            except:
                pass
        
        if config.get('collection_name', '').startswith('AIC_2024_1'):
            issues.append("⚠️  Using legacy collection name 'AIC_2024_1'")
        
        if issues:
            print("\nConfiguration Issues:")
            for issue in issues:
                print(f"   {issue}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return False

def check_data():
    """Check data directories"""
    check_section("Data Directories")
    
    paths = {
        "Keyframes": Path("/home/ir/keyframes_new/keyframes"),
        "Videos": Path("/home/ir/drive_download/batch_1/mlcv1/Datasets/HCMAI24/updated/videos/batch1"),
        "Embeddings": Path("/home/ir/keyframes_new/embedding/embeddings"),
    }
    
    for name, path in paths.items():
        if path.exists():
            # Count subdirectories
            subdirs = len(list(path.iterdir())) if path.is_dir() else 0
            print(f"✅ {name:15s} - {path} ({subdirs} items)")
        else:
            print(f"❌ {name:15s} - Not found: {path}")

def check_frontend():
    """Check frontend deployment"""
    check_section("Frontend")
    
    frontend_path = Path("/var/www/retrieval-frontend")
    
    if frontend_path.exists():
        print(f"✅ Frontend deployed: {frontend_path}")
    else:
        print(f"⚠️  Frontend not found at: {frontend_path}")
        print("   May be running from: /home/ir/retrievalBaseline/frontend")
    
    # Check if nginx is serving
    success, output, _ = run_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:8007", "Check frontend")
    
    if success and output == '200':
        print(f"✅ Frontend accessible at http://localhost:8007")
    else:
        print(f"⚠️  Frontend not accessible (HTTP {output})")

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        Video Retrieval System - Health Check                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    checks = [
        check_python_dependencies,
        check_gpu,
        check_milvus,
        check_backend,
        check_config,
        check_data,
        check_frontend
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Error during check: {e}")
            results.append(False)
    
    # Summary
    check_section("Summary")
    
    passed = sum(1 for r in results if r is True)
    total = len([r for r in results if r is not None])
    
    print(f"Checks passed: {passed}/{total}")
    
    if all(r for r in results if r is not None):
        print("\n✅ All systems operational!")
    else:
        print("\n⚠️  Some issues detected - review output above")
    
    print("\n" + "="*60)
    print("\nFor detailed analysis, see:")
    print("  - /home/ir/SYSTEM_EVALUATION_REPORT.md")
    print("  - /home/ir/QUICK_ACTION_PLAN.md")
    print("\nBackend logs:")
    print("  - tail -f /home/ir/retrievalBaseline/backend/backend.log")
    print()

if __name__ == "__main__":
    main()
