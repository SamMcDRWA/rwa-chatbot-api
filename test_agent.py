#!/usr/bin/env python3
"""
Test script for RWA Agent
"""
import os
from dotenv import load_dotenv
from src.agent import RWAAgent

load_dotenv()

def test_agent():
    """Test the RWA Agent with problematic queries"""
    print("🤖 Testing RWA Agent...")
    
    try:
        # Initialize agent
        agent = RWAAgent()
        print("✅ Agent initialized successfully")
        
        # Test queries
        test_queries = [
            "hi",
            "hello",
            "help",
            "details on nms",
            "details on 13.20",
            "tell me about 2.30",
            "find financial reports"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing: '{query}'")
            print("-" * 50)
            
            # Debug the analysis
            analysis = agent._analyze_query(query)
            print(f"Analysis: {analysis}")
            
            result = agent.chat(query)
            print(f"Response: {result['response']}")
            print(f"Agent used: {result.get('agent_used', False)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent()
