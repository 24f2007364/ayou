"""
AI Stack Builder Module
Handles AI-powered tool stack generation using Groq API
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
import requests
from datetime import datetime

class StackBuilder:
    def __init__(self):
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.groq_base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # Enhanced keyword mapping for accurate category detection
        self.category_keywords = {
            'Writing & Content': [
                'write', 'writing', 'content', 'blog', 'article', 'copy', 'copywriting',
                'text', 'essay', 'book', 'novel', 'script', 'screenplay', 'story',
                'grammar', 'proofreading', 'editing', 'documentation', 'technical writing',
                'social media post', 'caption', 'headline', 'slogan', 'marketing copy'
            ],
            'Image Generation': [
                'image', 'photo', 'picture', 'visual', 'graphic', 'illustration',
                'art', 'artwork', 'design', 'logo', 'icon', 'banner', 'poster',
                'thumbnail', 'avatar', 'portrait', 'sketch', 'drawing', 'painting',
                'infographic', 'chart', 'diagram', 'mockup', 'prototype'
            ],
            'Video Editing': [
                'video', 'movie', 'film', 'clip', 'footage', 'editing', 'montage',
                'animation', 'motion', 'cinematic', 'vlog', 'youtube', 'tiktok',
                'reel', 'short', 'trailer', 'documentary', 'commercial', 'ads'
            ],
            'Audio & Music': [
                'audio', 'sound', 'music', 'voice', 'speech', 'podcast', 'narration',
                'voiceover', 'singing', 'song', 'beat', 'melody', 'composition',
                'mixing', 'mastering', 'recording', 'jingle', 'soundeffect'
            ],
            'Code & Development': [
                'code', 'coding', 'programming', 'development', 'software', 'app',
                'website', 'web', 'frontend', 'backend', 'api', 'database',
                'javascript', 'python', 'react', 'node', 'html', 'css',
                'debugging', 'testing', 'deployment', 'github', 'git'
            ],
            'Data & Analytics': [
                'data', 'analytics', 'analysis', 'statistics', 'visualization',
                'chart', 'graph', 'dashboard', 'report', 'insights', 'metrics',
                'sql', 'database', 'spreadsheet', 'excel', 'csv', 'big data',
                'machine learning', 'ai model', 'prediction', 'forecasting'
            ],
            'Business & Productivity': [
                'business', 'productivity', 'management', 'planning', 'strategy',
                'workflow', 'automation', 'crm', 'sales', 'marketing', 'lead',
                'customer', 'project', 'task', 'schedule', 'calendar', 'meeting',
                'presentation', 'proposal', 'invoice', 'accounting', 'finance'
            ],
            'AI & Machine Learning': [
                'ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning',
                'neural network', 'model', 'training', 'prediction', 'classification',
                'nlp', 'natural language', 'computer vision', 'chatbot', 'assistant',
                'automation', 'algorithm', 'tensorflow', 'pytorch', 'huggingface'
            ],
            'Design & UI/UX': [
                'design', 'ui', 'ux', 'interface', 'user experience', 'wireframe',
                'prototype', 'mockup', 'layout', 'typography', 'color', 'branding',
                'logo', 'identity', 'figma', 'sketch', 'adobe', 'photoshop'
            ],
            'Social Media': [
                'social media', 'instagram', 'facebook', 'twitter', 'linkedin',
                'tiktok', 'youtube', 'snapchat', 'pinterest', 'reddit',
                'post', 'content calendar', 'hashtag', 'engagement', 'follower',
                'influencer', 'viral', 'trending', 'community', 'brand awareness'
            ],
            'E-commerce': [
                'ecommerce', 'e-commerce', 'online store', 'shop', 'shopping',
                'product', 'inventory', 'order', 'payment', 'checkout',
                'shopify', 'woocommerce', 'amazon', 'ebay', 'marketplace',
                'dropshipping', 'fulfillment', 'shipping', 'customer service'
            ],
            'Communication': [
                'communication', 'chat', 'messaging', 'email', 'newsletter',
                'notification', 'sms', 'call', 'video call', 'meeting',
                'collaboration', 'team', 'slack', 'discord', 'zoom', 'teams'
            ]
        }
    
    def extract_relevant_categories(self, prompt: str) -> List[str]:
        """Extract relevant categories from user prompt using keyword matching"""
        prompt_lower = prompt.lower()
        relevant_categories = []
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                # Exact phrase matching gets higher score
                if keyword in prompt_lower:
                    score += 2
                # Word boundary matching for individual words
                for word in keyword.split():
                    if re.search(r'\b' + re.escape(word) + r'\b', prompt_lower):
                        score += 1
            
            if score > 0:
                category_scores[category] = score
        
        # Sort by score and return top categories
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 3 categories or all if less than 3
        relevant_categories = [cat for cat, score in sorted_categories[:3]]
          # If no categories found, return all (fallback)
        if not relevant_categories:
            relevant_categories = list(self.category_keywords.keys())
        
        return relevant_categories
    
    def get_filtered_tools(self, db_connection, categories: List[str]) -> List[Dict]:
        """Get tools from database filtered by categories"""
        try:
            if hasattr(db_connection, 'execute'):  # SupabaseConnection
                # For Supabase, we need to handle category filtering
                all_tools = db_connection.execute(
                    'SELECT name, description, category, key_features, average_rating, link FROM tools'
                ).fetchall()
                
                print(f"DEBUG: Fetched {len(all_tools)} tools from database")
                print(f"DEBUG: First tool type: {type(all_tools[0]) if all_tools else 'No tools'}")
                
                # Filter tools by categories
                filtered_tools = []
                for tool in all_tools:
                    # Handle both dict and Row objects
                    if isinstance(tool, dict):
                        tool_dict = tool
                    else:
                        tool_dict = dict(tool)
                    
                    if tool_dict.get('category') in categories:
                        # Parse key_features if it's JSON string
                        if isinstance(tool_dict.get('key_features'), str):
                            try:
                                tool_dict['key_features'] = json.loads(tool_dict['key_features'])
                            except:                                tool_dict['key_features'] = []
                        filtered_tools.append(tool_dict)
                
                print(f"DEBUG: Filtered to {len(filtered_tools)} tools")
                return filtered_tools
            else:                # For SQLite
                category_placeholders = ','.join(['?' for _ in categories])
                query = f'''
                    SELECT name, description, category, key_features, 
                           COALESCE(average_rating, 0) as average_rating, link, logo_url 
                    FROM tools 
                    WHERE category IN ({category_placeholders})
                '''
                tools = db_connection.execute(query, categories).fetchall()
                
                result = []
                for tool in tools:
                    tool_dict = dict(tool)                    # Parse key_features if it's JSON string
                    if isinstance(tool_dict.get('key_features'), str):
                        try:
                            tool_dict['key_features'] = json.loads(tool_dict['key_features'])
                        except:
                            tool_dict['key_features'] = []
                    result.append(tool_dict)
                
                return result
                
        except Exception as e:
            print(f"Error fetching tools: {e}")
            return []    
    def create_groq_prompt(self, user_prompt: str, tools_data: List[Dict]) -> str:
        """Create a structured prompt for Groq API"""
        # Clean tools data - only send what AI needs, NOT logos!
        clean_tools = []
        for tool in tools_data:
            clean_tool = {
                'name': tool.get('name', ''),
                'description': tool.get('description', ''),
                'category': tool.get('category', ''),
                'key_features': tool.get('key_features', []),
                'average_rating': tool.get('average_rating', 0),
                'link': tool.get('link', '')
                # Deliberately NOT including logo_url - AI doesn't need it!
            }
            clean_tools.append(clean_tool)
        
        tools_json = json.dumps(clean_tools, indent=2)
        
        prompt = f"""
You are an AI Stack Builder expert. Your task is to analyze a user\\'s request and create a step-by-step workflow using the available AI tools.

USER REQUEST: "{user_prompt}"

AVAILABLE TOOLS:
{tools_json}

INSTRUCTIONS:
1. Analyze the user\\'s request and break it down into logical steps
2. For each step, recommend the most suitable tool(s) from the available tools
3. Provide a clear, actionable workflow
4. Focus on tools with higher ratings when multiple options exist
5. Return your response in this EXACT JSON format:

{{
  "workflow": [
    {{
      "step": 1,
      "title": "Step title",
      "description": "Detailed description of what to do in this step",
      "tools": [
        {{
          "name": "Tool Name",
          "reason": "Why this tool is recommended for this step"
        }}
      ]
    }}
  ],
  "summary": "Brief summary of the entire workflow"
}}

IMPORTANT: 
- Only use tools from the provided list
- Ensure the JSON is valid and follows the exact format
- Each step should have at least one tool recommendation
- Be specific about how each tool contributes to the workflow
- Steps should be in logical order
"""
        return prompt
    
    def call_groq_api(self, prompt: str) -> Optional[Dict]:
        """Make API call to Groq"""
        if not self.groq_api_key:
            return None
        
        headers = {
            'Authorization': f'Bearer {self.groq_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': "llama-3.1-8b-instant",  # Free tier model
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.0,  # Lower temperature for more consistent results
            'max_tokens': 2048        }
        
        try:
            response = requests.post(
                self.groq_base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Groq API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return None
    
    def parse_groq_response(self, response: Dict) -> Optional[Dict]:
        """Parse Groq API response and extract workflow"""
        try:
            content = response['choices'][0]['message']['content']
            print(f"DEBUG: Raw Groq response content: {content[:500]}...") # Log more content

            # Attempt to extract JSON robustly
            # Regex to find JSON block, allowing for ```json ... ``` or just { ... }
            match = re.search(r"```json\s*(\{.*?\})\s*```|(\{.*?\})", content, re.DOTALL)
            
            if not match:
                print("DEBUG: No JSON structure found in response using regex")
                # Fallback: try to find the first '{' and last '}'
                json_start_fallback = content.find('{')
                json_end_fallback = content.rfind('}')
                if json_start_fallback != -1 and json_end_fallback != -1 and json_start_fallback < json_end_fallback:
                    json_content = content[json_start_fallback : json_end_fallback + 1]
                    print(f"DEBUG: Extracted JSON content using fallback: {json_content[:200]}...")
                else:
                    print("DEBUG: Fallback JSON extraction also failed.")
                    return None
            else:
                # Get the content of the first non-None group
                json_content = next(g for g in match.groups() if g is not None)
                print(f"DEBUG: Extracted JSON content using regex: {json_content[:200]}...")

            # Pre-processing: Attempt to fix common JSON errors
            # 1. Replace problematic newlines within strings (common issue)
            # This regex looks for newlines not preceded or followed by a quote, comma, brace or bracket
            # and not at the start/end of the string, then replaces them with a space.
            # It's a heuristic and might need refinement.
            # json_content = re.sub(r'(?<![\"{}[\],\s])\n(?![\"{}[\],\s])', ' ', json_content)
            
            # 2. Ensure proper escaping of backslashes and quotes (more advanced, be careful)
            # json_content = json_content.replace('\\', '\\\\') # Escape backslashes
            # json_content = re.sub(r'(?<!\\)"', '\\"', json_content) # Escape unescaped quotes - very tricky

            try:
                workflow_data = json.loads(json_content)
                print("DEBUG: Successfully parsed JSON")
                return workflow_data
            except json.JSONDecodeError as e:
                print(f"Error parsing Groq response JSON: {e}")
                # Log the problematic part of the JSON
                # The error object 'e' has lineno, colno, pos attributes
                start = max(0, e.pos - 30)
                end = min(len(json_content), e.pos + 30)
                problematic_snippet = json_content[start:end]
                print(f"DEBUG: Problematic JSON snippet (around char {e.pos}, line {e.lineno}, col {e.colno}): ...{problematic_snippet}...")
                return None
            
        except Exception as e:
            print(f"Error in parse_groq_response (outer try-except): {e}")
            import traceback
            print(f"DEBUG: Full traceback for parse_groq_response: {traceback.format_exc()}")
            return None
    
    def build_stack(self, user_prompt: str, db_connection) -> Dict:
        """Main method to build AI stack based on user prompt"""
        try:
            print("DEBUG: Step 1 - Extracting categories")
            # Step 1: Extract relevant categories
            relevant_categories = self.extract_relevant_categories(user_prompt)
            print(f"DEBUG: Found categories: {relevant_categories}")
            
            print("DEBUG: Step 2 - Getting filtered tools")
            # Step 2: Get filtered tools from database
            tools_data = self.get_filtered_tools(db_connection, relevant_categories)            
            if not tools_data:
                print(f"DEBUG: No tools found for categories: {relevant_categories}")
                return {
                    'success': False,
                    'error': 'no_tools_found',
                    'message': f'No relevant tools found for your request. Please try refining your prompt or use different keywords. We searched in categories: {", ".join(relevant_categories)}',
                    'categories': relevant_categories
                }
            
            print("DEBUG: Step 3 - Creating Groq prompt")
            # Step 3: Create prompt for Groq
            groq_prompt = self.create_groq_prompt(user_prompt, tools_data)
            print("DEBUG: Groq prompt created successfully")
            
            print("DEBUG: Step 4 - Calling Groq API")
            # Step 4: Call Groq API
            groq_response = self.call_groq_api(groq_prompt) 
            print(groq_response)           
            if not groq_response:
                return {
                    'success': False,
                    'error': 'ai_service_error',
                    'message': 'Oops! Our AI assistant is taking a coffee break ☕ Please try again in a moment.',
                    'categories': relevant_categories
                }
            print("DEBUG: Step 5 - Parsing Groq response")
            # Step 5: Parse response
            workflow = self.parse_groq_response(groq_response)            
            if not workflow:
                return {
                    'success': False,
                    'error': 'parsing_error',
                    'message': 'Hmm, our AI got a bit confused 🤔 Could you try rephrasing your request?',
                    'categories': relevant_categories
                }
            print("DEBUG: Step 6 - Enhancing workflow")
            # Step 6: Enhance workflow with tool details
            enhanced_workflow = self.enhance_workflow_with_tool_details(workflow, tools_data, db_connection)
            print("DEBUG: Workflow enhanced successfully")
            
            print("DEBUG: Preparing return data")
            return_data = {
                'success': True,
                'workflow': enhanced_workflow,
                'categories': relevant_categories,
                'total_tools': len(tools_data)
            }
            print("DEBUG: Return data prepared successfully")
            return return_data
        except Exception as e:
            print(f"Error in build_stack: {e}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': 'Oops! Something went wrong in our AI kitchen 👨‍🍳 Please try again!',
                'categories': []            }

    def enhance_workflow_with_tool_details(self, workflow: Dict, tools_data: List[Dict], db_connection) -> Dict:
        """Enhance workflow with full tool details"""
        print(f"DEBUG: Starting enhance_workflow_with_tool_details")
        print(f"DEBUG: workflow type: {type(workflow)}")
        print(f"DEBUG: workflow keys: {list(workflow.keys()) if isinstance(workflow, dict) else 'Not a dict'}")
        print(f"DEBUG: tools_data length: {len(tools_data)}")
        
        try:
            tools_dict = {tool['name']: tool for tool in tools_data}
            print(f"DEBUG: Created tools_dict with {len(tools_dict)} tools")
            
            enhanced_workflow = workflow.copy()
            print(f"DEBUG: Copied workflow")
            
            workflow_steps = enhanced_workflow.get('workflow', [])
            print(f"DEBUG: Found {len(workflow_steps)} workflow steps")
            
            for i, step in enumerate(workflow_steps):
                print(f"DEBUG: Processing step {i}: {step.get('title', 'No title')}")
                enhanced_tools = []
                step_tools = step.get('tools', [])
                print(f"DEBUG: Step {i} has {len(step_tools)} tools")
                
                for j, tool_ref in enumerate(step_tools):
                    print(f"DEBUG: Processing tool {j}: {tool_ref}")
                    tool_name = tool_ref.get('name')
                    print(f"DEBUG: Tool name: {tool_name}")
                    
                    if tool_name in tools_dict:
                        print(f"DEBUG: Found tool {tool_name} in tools_dict")
                        tool_details = tools_dict[tool_name].copy()                        
                        tool_details['reason'] = tool_ref.get('reason', '')
                        enhanced_tools.append(tool_details)
                        print(f"DEBUG: Added enhanced tool {tool_name}")
                    else:
                        print(f"DEBUG: Tool {tool_name} not found in tools_dict")
                        
                step['tools'] = enhanced_tools
                print(f"DEBUG: Updated step {i} with {len(enhanced_tools)} enhanced tools")
            print(f"DEBUG: enhance_workflow_with_tool_details completed successfully")
            
            # Collect all tool names for logo fetching
            all_tool_names = []
            for step in workflow_steps:
                for tool in step.get('tools', []):
                    tool_name = tool.get('name', '')
                    if tool_name:
                        all_tool_names.append(tool_name)
            
            # Fetch logos for all tools at once
            print(f"DEBUG: Fetching logos for {len(all_tool_names)} tools: {all_tool_names}")
            tool_logos = self.get_tool_logos(db_connection, all_tool_names)
            print(f"DEBUG: Retrieved {len(tool_logos)} logos")
            
            # Transform the structure to match frontend expectations
            frontend_workflow = {
                'workflow_title': f"AI Workflow: {enhanced_workflow.get('summary', 'Custom AI Stack')}",
                'workflow_description': enhanced_workflow.get('summary', 'AI-powered workflow generated based on your requirements'),
                'estimated_time': 'Variable',
                'difficulty_level': 'Intermediate',
                'steps': []
            }
            
            for i, step in enumerate(enhanced_workflow.get('workflow', [])):
                frontend_step = {
                    'title': step.get('title', f'Step {i+1}'),
                    'description': step.get('description', ''),
                    'expected_outcome': step.get('expected_outcome', ''),
                    'recommended_tools': []
                }
                  # Transform tools to match frontend expectations
                for tool in step.get('tools', []):
                    tool_name = tool.get('name', '')
                    frontend_tool = {
                        'tool_name': tool_name,
                        'tool_category': tool.get('category', ''),
                        'tool_url': tool.get('link', ''),
                        'tool_id': None,  # We don't have tool IDs in our current structure
                        'tool_verified': True,  # Assume verified since they're from our database
                        'why_recommended': tool.get('reason', ''),
                        'setup_notes': None,
                        'logo_url': tool_logos.get(tool_name, '')  # Add logo URL here!
                    }
                    frontend_step['recommended_tools'].append(frontend_tool)
                
                frontend_workflow['steps'].append(frontend_step)
            
            print(f"DEBUG: Transformed workflow structure for frontend")
            print(f"DEBUG: Frontend workflow has {len(frontend_workflow['steps'])} steps")
            
            return frontend_workflow
            
        except Exception as e:
            print(f"DEBUG: Error in enhance_workflow_with_tool_details: {e}")
            import traceback
            print(f"DEBUG: enhance_workflow_with_tool_details traceback: {traceback.format_exc()}")
            raise
    
    def transform_for_frontend(self, workflow_data, db_connection):
        """Transform workflow data to match frontend expectations and fetch logos"""
        print("DEBUG: Starting transform_for_frontend")
        
        # Collect all tool names from the workflow
        all_tool_names = []
        for step in workflow_data.get('workflow', []):
            for tool in step.get('tools', []):
                tool_name = tool.get('name', '')
                if tool_name:
                    all_tool_names.append(tool_name)
        
        # Fetch logos for all tools at once
        print(f"DEBUG: Fetching logos for {len(all_tool_names)} tools: {all_tool_names}")
        tool_logos = self.get_tool_logos(db_connection, all_tool_names)
        print(f"DEBUG: Retrieved {len(tool_logos)} logos")
        
        # Create the structure the frontend expects
        frontend_workflow = {
            'workflow_title': f"AI Workflow: {workflow_data.get('summary', 'Custom AI Stack')}",
            'workflow_description': workflow_data.get('summary', 'AI-powered workflow generated based on your requirements'),
            'estimated_time': 'Variable',
            'difficulty_level': 'Intermediate',
            'steps': []
        }
        
        # Transform each step
        for i, step in enumerate(workflow_data.get('workflow', [])):
            frontend_step = {
                'title': step.get('title', f'Step {i+1}'),
                'description': step.get('description', ''),
                'expected_outcome': step.get('expected_outcome', ''),
                'recommended_tools': []
            }
            
            # Transform tools to match frontend expectations
            for tool in step.get('tools', []):
                tool_name = tool.get('name', '')
                frontend_tool = {
                    'tool_name': tool_name,
                    'tool_category': tool.get('category', ''),
                    'tool_url': tool.get('link', ''),
                    'tool_id': None,
                    'tool_verified': True,
                    'why_recommended': tool.get('reason', ''),
                    'setup_notes': None,
                    'logo_url': tool_logos.get(tool_name, '')  # Add logo URL here!
                }
                frontend_step['recommended_tools'].append(frontend_tool)
            print("Debug::::",frontend_step['recommended_tools'])
            frontend_workflow['steps'].append(frontend_step)
        
        print(f"DEBUG: Transformed workflow with {len(frontend_workflow['steps'])} steps and logos")
        return frontend_workflow
    
    def save_stack(self, user_id: int, prompt: str, workflow: Dict, db_connection) -> bool:
        """Save generated stack for logged-in users"""
        try:
            stack_data = {
                'user_id': user_id,
                'prompt': prompt,
                'workflow': json.dumps(workflow),
                'created_at': datetime.now().isoformat()
            }
            if hasattr(db_connection, 'execute'):  # SupabaseConnection
                # For Supabase
                response = db_connection.session.post(
                    f"{db_connection.base_url}/rest/v1/user_stacks",
                    json=stack_data
                )
                return response.status_code in [200, 201]
            else:
                # For SQLite - create table if not exists
                db_connection.execute('''
                    CREATE TABLE IF NOT EXISTS user_stacks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        prompt TEXT NOT NULL,
                        workflow TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                db_connection.execute('''
                    INSERT INTO user_stacks (user_id, prompt, workflow, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, prompt, json.dumps(workflow), datetime.now().isoformat()))
                db_connection.commit()
                return True
                
        except Exception as e:
            print(f"Error saving stack: {e}")
            return False
    
    def get_user_stacks(self, user_id: int, db_connection) -> List[Dict]:
        """Get saved stacks for a user"""
        try:
            if hasattr(db_connection, 'execute'):  # SupabaseConnection
                response = db_connection.session.get(
                    f"{db_connection.base_url}/rest/v1/user_stacks?user_id=eq.{user_id}&order=created_at.desc"
                )
                if response.status_code == 200:
                    stacks = response.json()
                    for stack in stacks:
                        if isinstance(stack.get('workflow'), str):
                            stack['workflow'] = json.loads(stack['workflow'])
                    return stacks
                return []
            else:
                # For SQLite - ensure table exists
                db_connection.execute('''
                    CREATE TABLE IF NOT EXISTS user_stacks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        prompt TEXT NOT NULL,
                        workflow TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                stacks = db_connection.execute('''
                    SELECT * FROM user_stacks 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                ''', (user_id,)).fetchall()
                
                result = []
                for stack in stacks:
                    stack_dict = dict(stack)
                    if isinstance(stack_dict.get('workflow'), str):
                        stack_dict['workflow'] = json.loads(stack_dict['workflow'])
                    result.append(stack_dict)
                return result
                
        except Exception as e:
            print(f"Error getting user stacks: {e}")
            return []
    
    def delete_user_stack(self, stack_id: int, user_id: int, db_connection) -> bool:
        """Delete a user's saved stack"""
        try:
            if hasattr(db_connection, 'execute'):  # SupabaseConnection
                response = db_connection.session.delete(
                    f"{db_connection.base_url}/rest/v1/user_stacks?id=eq.{stack_id}&user_id=eq.{user_id}"
                )
                return response.status_code in [200, 204]
            else:
                # For SQLite
                cursor = db_connection.execute('''
                    DELETE FROM user_stacks 
                    WHERE id = ? AND user_id = ?
                ''', (stack_id, user_id))
                db_connection.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error deleting stack: {e}")
            return False
    
    def track_free_usage(self, session) -> tuple:
        """Track free usage for non-logged-in users"""
        print(f"DEBUG: Session contents at start of tracking: {dict(session)}")
        free_uses = session.get('stack_builder_free_uses', 0)
        max_free_uses = 1
        
        print(f"DEBUG: Free usage tracking - current uses: {free_uses}, max: {max_free_uses}")
        print(f"DEBUG: Session ID (if available): {getattr(session, 'sid', 'No SID')}")
        
        can_use = free_uses < max_free_uses
        uses_remaining = max_free_uses - free_uses
        
        print(f"DEBUG: Can use: {can_use}, uses remaining: {uses_remaining}")
        return can_use, uses_remaining
    
    def increment_free_usage(self, session):
        """Increment free usage counter"""
        old_uses = session.get('stack_builder_free_uses', 0)
        new_uses = old_uses + 1
        session['stack_builder_free_uses'] = new_uses
        session.permanent = True
        
        # Force session to be modified
        session.modified = True
        
        print(f"DEBUG: Incremented free usage from {old_uses} to {new_uses}")
        print(f"DEBUG: Session after increment: {dict(session)}")
        print(f"DEBUG: Session permanent: {session.permanent}")
        print(f"DEBUG: Session modified: {session.modified}")
    
    def track_free_usage_by_ip(self, db_connection, client_ip: str) -> tuple:
        """Track free usage by IP address instead of session"""
        print(f"DEBUG: Tracking usage for IP: {client_ip}")
        
        try:
            max_free_uses = 1 
            
            # Get today's date
            from datetime import date # Removed datetime import as it's not used here
            today = date.today().isoformat() # e.g., '2023-10-26'
            
            current_uses = 0
            if hasattr(db_connection, 'session'):  # SupabaseConnection
                # For Supabase, check usage table
                # The unique constraint is on (ip_address, usage_date)
                response = db_connection.session.get(
                    f"{db_connection.base_url}/rest/v1/free_usage?ip_address=eq.{client_ip}&usage_date=eq.{today}&select=usage_count"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data: # If a record exists
                        current_uses = data[0]['usage_count']
                    # If no data, current_uses remains 0, which is correct
                else:
                    # Log error but proceed as if no uses (safer for user, but needs monitoring)
                    print(f"DEBUG: Supabase API error when fetching free_usage: {response.status_code} - {response.text}")
                    # Fallback to allowing use if Supabase check fails, to avoid blocking users due to API issues.
                    # Consider if this is the desired behavior or if it should be more restrictive.
                    # For now, if Supabase fails, we assume 0 uses to not block the user.
                    current_uses = 0 
            else:
                # For SQLite
                cursor = db_connection.execute(
                    "SELECT usage_count FROM free_usage WHERE ip_address = ? AND usage_date = ?",
                    (client_ip, today)
                )
                result = cursor.fetchone()
                if result:
                    current_uses = result['usage_count']
            
            can_use = current_uses < max_free_uses
            uses_remaining = max(0, max_free_uses - current_uses) # Ensure uses_remaining is not negative
            
            print(f"DEBUG: IP {client_ip} has used {current_uses}/{max_free_uses} today. Can use: {can_use}")
            return can_use, uses_remaining
            
        except Exception as e:
            print(f"DEBUG: Error tracking IP usage: {e}. Allowing usage as a fallback.")
            import traceback
            print(f"DEBUG: Full traceback for track_free_usage_by_ip: {traceback.format_exc()}")
            # If we can't track, allow usage by default.
            return True, 1

    def increment_free_usage_by_ip(self, db_connection, client_ip: str):
        """Increment free usage counter by IP"""
        print(f"DEBUG: Incrementing usage for IP: {client_ip}")
        
        try:
            from datetime import date
            today = date.today().isoformat()
            
            if hasattr(db_connection, 'session'):  # SupabaseConnection
                # Check if a record for this IP and date already exists
                get_response = db_connection.session.get(
                    f"{db_connection.base_url}/rest/v1/free_usage?ip_address=eq.{client_ip}&usage_date=eq.{today}&select=id,usage_count"
                )

                if get_response.status_code == 200:
                    data = get_response.json()
                    if data: # Record exists, update it
                        record_id = data[0]['id']
                        current_count = data[0]['usage_count']
                        new_count = current_count + 1
                        
                        patch_response = db_connection.session.patch(
                            f"{db_connection.base_url}/rest/v1/free_usage?id=eq.{record_id}",
                            json={'usage_count': new_count}
                        )
                        if patch_response.status_code in [200, 204]:
                            print(f"DEBUG: Supabase: Updated IP usage for {client_ip} to {new_count}")
                        else:
                            print(f"DEBUG: Supabase: Failed to update IP usage for {client_ip}. Status: {patch_response.status_code} - {patch_response.text}")
                    else: # No record exists, insert a new one
                        post_response = db_connection.session.post(
                            f"{db_connection.base_url}/rest/v1/free_usage",
                            json={
                                'ip_address': client_ip,
                                'usage_date': today,
                                'usage_count': 1 # Initial count is 1
                            }
                        )
                        if post_response.status_code == 201: # 201 Created
                            print(f"DEBUG: Supabase: Created new IP usage record for {client_ip}")
                        else:
                            print(f"DEBUG: Supabase: Failed to create IP usage record for {client_ip}. Status: {post_response.status_code} - {post_response.text}")
                else:
                    print(f"DEBUG: Supabase: Error checking existing IP usage for {client_ip}. Status: {get_response.status_code} - {get_response.text}")
            else:
                # For SQLite
                # Try to update existing record
                cursor = db_connection.execute(
                    "UPDATE free_usage SET usage_count = usage_count + 1 WHERE ip_address = ? AND usage_date = ?",
                    (client_ip, today)
                )
                
                if cursor.rowcount == 0:
                    # Insert new record if update didn't affect any rows
                    db_connection.execute(
                        "INSERT INTO free_usage (ip_address, usage_date, usage_count) VALUES (?, ?, 1)",
                        (client_ip, today)
                    )
                    print(f"DEBUG: SQLite: Created new IP usage record for {client_ip}")
                else:
                    print(f"DEBUG: SQLite: Updated IP usage for {client_ip}")
                
                db_connection.commit()
                
        except Exception as e:
            print(f"DEBUG: Error incrementing IP usage: {e}")
            import traceback
            print(f"DEBUG: Full traceback for increment_free_usage_by_ip: {traceback.format_exc()}")

    def build_stack_with_limits(self, user_prompt: str, db_connection, user_id: int = None, session=None, client_ip: str = None) -> Dict:
        """Build stack with usage limits for non-logged-in users"""
        print(f"DEBUG: build_stack_with_limits called - user_id: {user_id}, session exists: {session is not None}, IP: {client_ip}")
        
        # Check usage limits for non-logged-in users
        if not user_id:
            print("DEBUG: Checking usage limits for non-logged-in user")
            
            # Try IP-based tracking first (more reliable)
            if client_ip:
                print("DEBUG: Using IP-based tracking")
                can_use, uses_remaining = self.track_free_usage_by_ip(db_connection, client_ip)
            elif session:
                print("DEBUG: Falling back to session-based tracking")
                can_use, uses_remaining = self.track_free_usage(session)
            else:
                print("DEBUG: No tracking method available, allowing usage")
                can_use, uses_remaining = True, 1
            
            if not can_use:
                print("DEBUG: Usage limit reached, returning error")
                return {
                    'success': False,
                    'error': 'free_limit_reached',
                    'message': 'You have reached the free usage limit. Please register to continue using the Stack Builder.'
                }
        else:
            print(f"DEBUG: Skipping usage limits - user is logged in (user_id: {user_id})")
        
        # Build the stack
        result = self.build_stack(user_prompt, db_connection)
        
        # Track usage for non-logged-in users if successful
        if result.get('success') and not user_id:
            print("DEBUG: Incrementing usage for successful generation")
            
            # Increment both IP and session tracking
            if client_ip:
                self.increment_free_usage_by_ip(db_connection, client_ip)
            if session:
                self.increment_free_usage(session)
        else:
            print(f"DEBUG: Not incrementing usage - success: {result.get('success')}, user_id: {user_id}")        
        return result
    
    def get_tool_logos(self, db_connection, tool_names: List[str]) -> Dict[str, str]:
        """Fetch logo URLs for specific tools by name"""
        try:
            if not tool_names:
                return {}
            
            print(f"DEBUG: Fetching logos for tools: {tool_names}")
            
            if hasattr(db_connection, 'session'):  # SupabaseConnection - use REST API
                logo_dict = {}
                for tool_name in tool_names:
                    try:
                        # Use Supabase REST API with case-insensitive search using ilike
                        # First try exact match
                        response = db_connection.session.get(
                            f"{db_connection.base_url}/rest/v1/tools?name=eq.{tool_name}&select=name,logo_url"
                        )
                        
                        if response.status_code == 200 and response.json():
                            data = response.json()[0]
                            logo_dict[tool_name] = data.get('logo_url', '')
                            print(f"DEBUG: Found exact match for {tool_name}: {data.get('logo_url', '')}")
                        else:
                            # Try case-insensitive search using ilike
                            response = db_connection.session.get(
                                f"{db_connection.base_url}/rest/v1/tools?name=ilike.{tool_name}&select=name,logo_url"
                            )
                            
                            if response.status_code == 200 and response.json():
                                data = response.json()[0]
                                logo_dict[tool_name] = data.get('logo_url', '')
                                print(f"DEBUG: Found case-insensitive match for {tool_name}: {data.get('logo_url', '')}")
                            else:
                                print(f"DEBUG: No match found for {tool_name}")
                                logo_dict[tool_name] = ''
                    except Exception as e:
                        print(f"DEBUG: Error fetching logo for {tool_name}: {e}")
                        logo_dict[tool_name] = ''
                        continue
                        
                print(f"DEBUG: Fetched logos for {len([k for k, v in logo_dict.items() if v])} out of {len(tool_names)} tools")
                return logo_dict
            else:
                # For SQLite - use SQL with case-insensitive search
                logo_dict = {}
                for tool_name in tool_names:
                    try:
                        query = 'SELECT name, logo_url FROM tools WHERE LOWER(name) = LOWER(?)'
                        results = db_connection.execute(query, (tool_name,)).fetchall()
                        
                        if results:
                            row = results[0]
                            if isinstance(row, dict):
                                logo_dict[tool_name] = row.get('logo_url', '')
                            else:
                                logo_dict[tool_name] = row[1] if row[1] else ''
                        else:
                            logo_dict[tool_name] = ''
                    except Exception as e:
                        print(f"DEBUG: Error fetching logo for {tool_name}: {e}")
                        logo_dict[tool_name] = ''
                        continue
                
                print(f"DEBUG: Fetched logos for {len([k for k, v in logo_dict.items() if v])} out of {len(tool_names)} tools")
                return logo_dict
            
        except Exception as e:
            print(f"Error fetching tool logos: {e}")
            return {}
