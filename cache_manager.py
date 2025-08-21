#!/usr/bin/env python3
"""
Utility for managing LLM cache
"""
import argparse
import sys
from agents.cache import get_cache, reset_cache



def show_stats():
    """Show cache statistics"""
    cache = get_cache()
    stats = cache.get_stats()
    
    print("=== CACHE STATISTICS ===")
    print(f"Size: {stats['size']}/{stats['max_size']}")
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate']}")
    print(f"Evictions: {stats['evictions']}")
    print(f"TTL: {stats['ttl_seconds']} seconds")
    print(f"Persistence: {'✅' if stats['persistence_enabled'] else '❌'}")


def show_cache_content():
    """Show cache content"""
    cache = get_cache()
    info = cache.get_cache_info()
    
    if not info:
        print("📭 Cache is empty")
        return
    
    print("=== CACHE CONTENT ===")
    print(f"{'Key':<15} {'Model':<15} {'Tokens':<8} {'Cost':<12} {'Accesses':<10} {'Age':<10} {'Preview'}")
    print("-" * 100)
    
    for entry in info[:20]:  # Show only first 20 records
        key = entry['key']
        model = entry['model'] or 'N/A'
        tokens = str(entry['tokens']) if entry['tokens'] else 'N/A'
        cost = f"${entry['cost']:.6f}" if entry['cost'] else 'N/A'
        access_count = str(entry['access_count'])
        age = f"{entry['age_seconds']}s"
        preview = entry['content_preview']
        
        print(f"{key:<15} {model:<15} {tokens:<8} {cost:<12} {access_count:<10} {age:<10} {preview}")
    
    if len(info) > 20:
        print(f"\n... and {len(info) - 20} more records")


def clear_cache():
    """Clear cache"""
    print("🗑️  Clearing cache...")
    cache = get_cache()
    cache.clear()
    print("✅ Cache cleared")


def cleanup_expired():
    """Clear expired records"""
    print("🧹 Clearing expired records...")
    cache = get_cache()
    cache.cleanup_expired()
    print("✅ Expired records removed")


def test_cache_performance():
    """Test cache performance"""
    print("🧪 Testing cache performance...")
    
    from langchain_core.messages import HumanMessage
    from agents.llm_provider import get_model_manager, ModelType
    import time
    
    # Get provider
    manager = get_model_manager()
    provider = manager.get_provider(ModelType.GENERATION)
    
    test_messages = [HumanMessage(content="Привет, это тест кэша!")]
    
    print("\n1. First request (no cache):")
    start_time = time.time()
    response1 = provider.invoke(test_messages)
    time1 = time.time() - start_time
    print(f"   ⏱️  Time: {time1:.2f}s")
    print(f"   📝 Answer: {response1.content[:50]}...")
    
    print("\n2. Second request (from cache):")
    start_time = time.time()
    response2 = provider.invoke(test_messages)
    time2 = time.time() - start_time
    print(f"   ⏱️  Time: {time2:.2f}s")
    print(f"   📝 Answer: {response2.content[:50]}...")
    
    speedup = time1 / time2 if time2 > 0 else float('inf')
    print(f"\n🚀 Speedup: {speedup:.1f}x")
    
    # Show statistics
    print("\nStatistics after test:")
    show_stats()


def configure_cache(max_size: int = None, ttl_seconds: int = None):
    """Configure cache parameters"""
    cache = get_cache()
    
    if max_size is not None:
        cache.max_size = max_size
        print(f"✅ Maximum cache size set: {max_size}")
    
    if ttl_seconds is not None:
        cache.ttl_seconds = ttl_seconds
        print(f"✅ TTL set: {ttl_seconds} seconds")
    
    show_stats()


def main():
    parser = argparse.ArgumentParser(description="Manage LLM cache")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Command to show statistics
    subparsers.add_parser('stats', help='Show cache statistics')
    
    # Command to show cache content
    subparsers.add_parser('show', help='Show cache content')
    
    # Command to clear cache
    subparsers.add_parser('clear', help='Clear cache')
    
    # Command to clear expired records
    subparsers.add_parser('cleanup', help='Remove expired records')
    
    # Command to test cache performance
    subparsers.add_parser('test', help='Test cache performance')
    
    # Command to configure cache
    config_parser = subparsers.add_parser('config', help='Configure cache')
    config_parser.add_argument('--max-size', type=int, help='Maximum cache size')
    config_parser.add_argument('--ttl', type=int, help='TTL in seconds')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'stats':
            show_stats()
            
        elif args.command == 'show':
            show_cache_content()
            
        elif args.command == 'clear':
            clear_cache()
            
        elif args.command == 'cleanup':
            cleanup_expired()
            
        elif args.command == 'test':
            test_cache_performance()
            
        elif args.command == 'config':
            configure_cache(args.max_size, args.ttl)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()