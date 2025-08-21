#!/usr/bin/env python3
"""
Utility for switching between different models and providers
"""
import argparse
import sys
from config import TweetAgentConfig
from agents.llm_provider import (
    get_model_manager, 
    ModelType, 
    ModelConfig, 
    ProviderType,
    reset_model_manager
)


def show_status():
    """Show current status of all providers"""
    print("=== CURRENT STATUS OF PROVIDERS ===")
    manager = get_model_manager()
    status = manager.get_status()
    
    for model_type, info in status.items():
        print(f"\n{model_type.upper()}:")
        print(f"  Provider: {info['provider']}")
        print(f"  Available: {'✅' if info['available'] else '❌'}")
        print(f"  Configuration:")
        for key, value in info['config'].items():
            print(f"    {key}: {value}")


def switch_model(model_type: str, model_name: str, temperature: float = None):
    """Switch model for a specific type"""
    try:
        # Validate model type
        if model_type not in [t.value for t in ModelType]:
            raise ValueError(f"Invalid model type: {model_type}")
        
        model_type_enum = ModelType(model_type)
        manager = get_model_manager()
        
        # Get current configuration
        current_provider = manager.get_provider(model_type_enum)
        current_config = current_provider.config
        
        # Create new configuration
        new_config = ModelConfig(
            provider=ProviderType.OPENAI,  # Currently only OpenAI is supported
            model_name=model_name,
            temperature=temperature if temperature is not None else current_config.temperature,
            max_tokens=current_config.max_tokens,
            timeout=current_config.timeout,
            cost_per_token=current_config.cost_per_token
        )
        
        # Switch
        manager.switch_provider(model_type_enum, new_config)
        
        print(f"✅ Successfully switched {model_type} to {model_name}")
        print(f"   Temperature: {new_config.temperature}")
        
        # Check availability
        new_provider = manager.get_provider(model_type_enum)
        if new_provider.is_available():
            print("✅ New model is available")
        else:
            print("❌ New model is not available")
            
    except Exception as e:
        print(f"❌ Error switching model: {e}")
        return False
    
    return True


def test_model_performance(model_type: str, test_message: str = "Привет, как дела?"):
    """Test model performance"""
    try:
        model_type_enum = ModelType(model_type)
        manager = get_model_manager()
        provider = manager.get_provider(model_type_enum)
        
        print(f"\n=== TEST PERFORMANCE OF {model_type.upper()} ===")
        print(f"Model: {provider}")
        print(f"Test message: {test_message}")
        
        from langchain_core.messages import HumanMessage
        import time
        
        start_time = time.time()
        response = provider.invoke([HumanMessage(content=test_message)])
        end_time = time.time()
        
        print(f"\n✅ Answer received in {end_time - start_time:.2f} seconds")
        print(f"Content: {response.content[:100]}...")
        print(f"Tokens: {response.tokens_used or 'N/A'}")
        print(f"Cost: ${response.cost:.6f}" if response.cost else "Cost: N/A")
        
    except Exception as e:
        print(f"❌ Error testing: {e}")


def compare_models(models: list, test_message: str = "Write a short tweet about AI"):
    """Compare performance of different models"""
    print(f"\n=== COMPARISON OF MODELS ===")
    print(f"Test message: {test_message}\n")
    
    results = []
    
    for model_name in models:
        try:
            # Switch to model
            print(f"Testing {model_name}...")
            switch_model("generation", model_name)
            
            manager = get_model_manager()
            provider = manager.get_provider(ModelType.GENERATION)
            
            from langchain_core.messages import HumanMessage
            import time
            
            start_time = time.time()
            response = provider.invoke([HumanMessage(content=test_message)])
            end_time = time.time()
            
            results.append({
                'model': model_name,
                'time': end_time - start_time,
                'tokens': response.tokens_used or 0,
                'cost': response.cost or 0.0,
                'content': response.content[:100] + "..." if len(response.content) > 100 else response.content
            })
            
        except Exception as e:
            print(f"❌ Error with {model_name}: {e}")
            results.append({
                'model': model_name,
                'time': None,
                'tokens': None,
                'cost': None,
                'content': f"Ошибка: {str(e)}"
            })
    
    # Show results
    print("\n=== RESULTS OF COMPARISON ===")
    for result in results:
        print(f"\n🤖 {result['model']}:")
        print(f"   ⏱️  Time: {result['time']:.2f}s" if result['time'] else "   ⏱️  Time: Error")
        print(f"   🔢 Tokens: {result['tokens']}" if result['tokens'] else "   🔢 Tokens: N/A")
        print(f"   💰 Cost: ${result['cost']:.6f}" if result['cost'] else "   💰 Cost: N/A")
        print(f"   📝 Answer: {result['content']}")


def add_fallback(model_type: str, model_name: str):
    """Add fallback provider"""
    try:
        model_type_enum = ModelType(model_type)
        manager = get_model_manager()
        
        # Create fallback configuration
        fallback_config = ModelConfig(
            provider=ProviderType.OPENAI,
            model_name=model_name,
            temperature=0.4,
            timeout=120,
            cost_per_token=0.000002
        )
        
        from agents.llm_provider import OpenAIProvider
        fallback_provider = OpenAIProvider(fallback_config)
        
        manager.add_fallback_provider(model_type_enum, fallback_provider)
        
        print(f"✅ Fallback provider {model_name} for {model_type} added")
        
    except Exception as e:
        print(f"❌ Error adding fallback: {e}")


def main():
    parser = argparse.ArgumentParser(description="Tweet Agent model management")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Command to show status
    subparsers.add_parser('status', help='Show status of providers')
    
    # Command to switch model
    switch_parser = subparsers.add_parser('switch', help='Переключить модель')
    switch_parser.add_argument('type', choices=['generation', 'critique', 'rewrite'], 
                              help='Model type')
    switch_parser.add_argument('model', help='Model name (e.g. gpt-4o)')
    switch_parser.add_argument('--temperature', type=float, help='Model temperature')
    
    # Command to test model
    test_parser = subparsers.add_parser('test', help='Test model')
    test_parser.add_argument('type', choices=['generation', 'critique', 'rewrite'], 
                            help='Model type')
    test_parser.add_argument('--message', default="Привет, как дела?", 
                           help='Test message')
    
    # Command to compare models
    compare_parser = subparsers.add_parser('compare', help='Compare models')
    compare_parser.add_argument('models', nargs='+', help='List of models to compare')
    compare_parser.add_argument('--message', default="Write a short tweet about AI", 
                              help='Test message')
    
    # Command to add fallback
    fallback_parser = subparsers.add_parser('fallback', help='Add fallback provider')
    fallback_parser.add_argument('type', choices=['generation', 'critique', 'rewrite'], 
                                help='Model type')
    fallback_parser.add_argument('model', help='Fallback model name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Reset model manager for clean state
    reset_model_manager()
    
    try:
        if args.command == 'status':
            show_status()
            
        elif args.command == 'switch':
            switch_model(args.type, args.model, args.temperature)
            
        elif args.command == 'test':
            test_model_performance(args.type, args.message)
            
        elif args.command == 'compare':
            compare_models(args.models, args.message)
            
        elif args.command == 'fallback':
            add_fallback(args.type, args.model)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()