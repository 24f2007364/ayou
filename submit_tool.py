"""
Tool Submission Module
Handles web scraping, tool data extraction, and processing using Groq API
"""

import os
import json
import re
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urljoin, urlparse
import time

class ToolSubmitter:
    def __init__(self):
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        self.groq_base_url = "https://api.groq.com/openai/v1/chat/completions"
          # Multiple header sets to rotate and avoid blocking
        self.header_sets = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            },
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        ]
        
        # Common logo selectors and patterns
        self.logo_selectors = [
            'img[alt*="logo" i]',
            'img[src*="logo" i]',
            'img.logo',
            '.logo img',
            '[class*="logo"] img',
            'img[alt*="brand" i]',
            'header img',
            '.navbar img',
            '.header img',
            'meta[property="og:image"]',
            'link[rel="icon"]',
            'link[rel="shortcut icon"]',
            'link[rel="apple-touch-icon"]'
        ]

    def scrape_tool_data(self, url: str) -> Dict[str, Any]:
        """
        Scrape tool data from the given URL
        """
        try:
            # Validate URL
            if not self._is_valid_url(url):
                return {"error": "Invalid URL format"}
            
            print(f"DEBUG: Scraping URL: {url}")
              # Make request with anti-blocking measures
            response = self._make_request(url)
            if not response:
                # If scraping fails, create basic data from URL
                return self._create_fallback_data(url)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic information
            tool_data = {
                "name": self._extract_title(soup, url),
                "description": self._extract_description(soup),
                "link": url,
                "logo_url": self._extract_logo(soup, url),
                "category": "Other",  # Will be determined by Groq
                "pricing_model": "Unknown",  # Will be determined by Groq
                "key_features": [],  # Will be filled by Groq
                "scraped_content": self._extract_content(soup)[:2000]  # First 2000 chars for Groq processing
            }
            
            print(f"DEBUG: Scraped data: {tool_data['name']}")
            return tool_data
            
        except Exception as e:
            print(f"Error scraping tool data: {e}")
            return {"error": f"Scraping failed: {str(e)}"}

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with error handling and anti-blocking measures"""
        import random
        
        # Try multiple times with different headers
        for attempt in range(len(self.header_sets)):
            try:
                headers = self.header_sets[attempt]
                
                # Add delay to avoid rate limiting
                time.sleep(random.uniform(1, 3))
                
                # Create session for better handling
                session = requests.Session()
                session.headers.update(headers)
                
                response = session.get(url, timeout=30, allow_redirects=True)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    print(f"403 Forbidden on attempt {attempt + 1}, trying different headers...")
                    continue
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                print(f"Request failed on attempt {attempt + 1}: {e}")
                if attempt == len(self.header_sets) - 1:
                    # Last attempt failed, try one more time with basic approach
                    try:
                        basic_response = requests.get(url, timeout=15)
                        if basic_response.status_code == 200:
                            return basic_response
                    except:
                        pass
                continue
        
        print(f"All attempts failed for URL: {url}")
        return None

    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract tool name from various sources"""
        # Try multiple sources in order of preference
        sources = [
            lambda: soup.find('meta', property='og:title'),
            lambda: soup.find('meta', attrs={'name': 'title'}),
            lambda: soup.find('title'),
            lambda: soup.find('h1'),
            lambda: soup.find('h2')
        ]
        
        for source in sources:
            try:
                element = source()
                if element:
                    title = element.get('content', '') if element.name == 'meta' else element.get_text()
                    title = title.strip()
                    if title and len(title) > 2:
                        # Clean up title
                        title = re.sub(r'\s+', ' ', title)
                        title = title.split('|')[0].split('-')[0].strip()  # Remove site name suffixes
                        return title[:100]  # Limit length
            except:
                continue
        
        # Fallback to domain name
        try:
            domain = urlparse(url).netloc
            return domain.replace('www.', '').split('.')[0].title()
        except:
            return "Unknown Tool"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract tool description from various sources"""
        sources = [
            lambda: soup.find('meta', property='og:description'),
            lambda: soup.find('meta', attrs={'name': 'description'}),
            lambda: soup.find('meta', attrs={'name': 'twitter:description'}),
            lambda: soup.find('.description'),
            lambda: soup.find('[class*="description"]'),
            lambda: soup.find('p')
        ]
        
        for source in sources:
            try:
                element = source()
                if element:
                    desc = element.get('content', '') if element.name == 'meta' else element.get_text()
                    desc = desc.strip()
                    if desc and len(desc) > 20:
                        # Clean up description
                        desc = re.sub(r'\s+', ' ', desc)
                        return desc[:500]  # Limit length
            except:
                continue
        
        return "AI-powered tool for enhanced productivity and automation."

    def _extract_logo(self, soup: BeautifulSoup, base_url: str) -> str:
        """Extract logo URL from various sources"""
        for selector in self.logo_selectors:
            try:
                if selector.startswith('meta') or selector.startswith('link'):
                    element = soup.select_one(selector)
                    if element:
                        url = element.get('content') or element.get('href')
                        if url:
                            return self._resolve_url(url, base_url)
                else:
                    elements = soup.select(selector)
                    for element in elements:
                        src = element.get('src')
                        if src and self._is_logo_url(src):
                            return self._resolve_url(src, base_url)
            except:
                continue
        
        # Fallback: try to find favicon
        try:
            favicon = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
            if favicon and favicon.get('href'):
                return self._resolve_url(favicon.get('href'), base_url)
        except:
            pass
        
        return ""

    def _is_logo_url(self, url: str) -> bool:
        """Check if URL likely contains a logo"""
        url_lower = url.lower()
        logo_indicators = ['logo', 'brand', 'icon', 'favicon']
        return any(indicator in url_lower for indicator in logo_indicators)

    def _resolve_url(self, url: str, base_url: str) -> str:
        """Resolve relative URLs to absolute URLs"""
        try:
            return urljoin(base_url, url)
        except:
            return url

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract relevant content for Groq processing"""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text

    def process_with_groq(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process scraped data with Groq API to extract and clean information
        """
        if not self.groq_api_key or self.groq_api_key == 'your-groq-api-key-here':
            print("DEBUG: Groq API key not configured, using intelligent fallbacks")
            return self._create_intelligent_fallback(scraped_data)
        
        try:
            print("DEBUG: Calling Groq API for tool analysis...")
            prompt = self._create_groq_prompt(scraped_data)
            response = self._call_groq_api(prompt)
            
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                print(f"DEBUG: Groq response received: {content[:200]}...")
                result = self._parse_groq_response(content)
                
                # Validate the result
                if not result.get("error") and self._validate_groq_result(result):
                    print("DEBUG: Groq processing successful")
                    return result
                else:
                    print("DEBUG: Groq result validation failed, using intelligent fallback")
                    return self._create_intelligent_fallback(scraped_data)
            else:
                print("DEBUG: No valid response from Groq API, using intelligent fallback")
                return self._create_intelligent_fallback(scraped_data)
                
        except Exception as e:
            print(f"DEBUG: Error processing with Groq: {e}, using intelligent fallback")
            return self._create_intelligent_fallback(scraped_data)

    def _create_groq_prompt(self, scraped_data: Dict[str, Any]) -> str:
        """Create prompt for Groq API"""
        tool_url = scraped_data.get('link', '')
        tool_name = scraped_data.get('name', 'Unknown')
        tool_description = scraped_data.get('description', 'No description')
        scraped_content = scraped_data.get('scraped_content', '')[:2000]  # Limit content size
        
        return f"""
You are an AI tool analyzer. Based on the website data below, extract accurate and UNIQUE information about this specific AI tool.

IMPORTANT: Do NOT use generic descriptions. Analyze the ACTUAL tool based on the URL and content provided.

TOOL INFORMATION:
- URL: {tool_url}
- Detected Name: {tool_name}
- Meta Description: {tool_description}
- Website Content: {scraped_content}

Based on this SPECIFIC tool's website content, provide a JSON response:
{{
    "name": "Exact tool name from the website (max 100 chars)",
    "description": "Unique, specific description of what THIS tool does (max 500 chars)",
    "category": "Choose the MOST appropriate ONE from: Writing & Content, Image Generation, Video Editing, Audio & Music, Code & Development, Data & Analytics, Business & Finance, Education & Learning, Design & Creative, Productivity, Marketing & Sales, Communication, Other",
    "pricing_model": "Based on website content, choose ONE: Free, Freemium, Paid, Enterprise, Open Source",
    "key_features": ["specific feature 1", "specific feature 2", "specific feature 3", "specific feature 4", "specific feature 5"]
}}

CRITICAL REQUIREMENTS:
1. The description MUST be unique to this specific tool - NO generic AI descriptions
2. Key features MUST be specific to what this tool actually does
3. Category MUST match the tool's primary function
4. Analyze the URL domain and content to understand what the tool really does
5. If it's a coding tool, use "Code & Development"
6. If it's for content creation, use "Writing & Content" 
7. If it's for design/graphics, use "Design & Creative"
8. Return ONLY valid JSON, no additional text

JSON Response:
"""

    def _call_groq_api(self, prompt: str) -> Optional[Dict]:
        """Make API call to Groq"""
        if not self.groq_api_key:
            return None
        
        headers = {
            'Authorization': f'Bearer {self.groq_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
            "top_p": 0.9
        }
        
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

    def _parse_groq_response(self, content: str) -> Dict[str, Any]:
        """Parse Groq API response"""
        try:
            # Extract JSON from the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                print("No JSON found in Groq response")
                return {"error": "Invalid response format from Groq"}
        except json.JSONDecodeError as e:
            print(f"Error parsing Groq JSON: {e}")
            return {"error": "Failed to parse Groq response"}

    def _create_fallback_data(self, url: str) -> Dict[str, Any]:
        """Create basic tool data when scraping fails"""
        try:
            domain = urlparse(url).netloc.replace('www.', '')
            tool_name = domain.split('.')[0].title()
            
            return {
                "name": tool_name,
                "description": f"AI-powered tool available at {domain}. Visit the website to learn more about its features and capabilities.",
                "link": url,
                "logo_url": "",
                "category": "Other",
                "pricing_model": "Unknown",
                "key_features": [],
                "scraped_content": f"Website: {url}. Tool name: {tool_name}. Domain: {domain}."
            }
        except:
            return {
                "name": "AI Tool",
                "description": "AI-powered tool for enhanced productivity and automation.",
                "link": url,
                "logo_url": "",
                "category": "Other",
                "pricing_model": "Unknown",                "key_features": [],
                "scraped_content": f"Website: {url}"
            }
    
    def submit_tool(self, url: str, email: str, country_of_origin: str = "Unknown") -> Dict[str, Any]:
        """
        Complete tool submission process
        """
        try:
            print(f"DEBUG: Starting tool submission for {url}")
            
            # Step 1: Scrape tool data
            scraped_data = self.scrape_tool_data(url)
            if "error" in scraped_data:
                print(f"DEBUG: Scraping failed: {scraped_data}")
                return scraped_data
            
            print(f"DEBUG: Scraping completed. Tool name: {scraped_data.get('name')}")
            print(f"DEBUG: Scraped description: {scraped_data.get('description', '')[:100]}...")
            
            # Step 2: Process with Groq/AI
            processed_data = self.process_with_groq(scraped_data)
            if "error" in processed_data:
                print(f"DEBUG: AI processing failed: {processed_data}")
                return processed_data
            
            print(f"DEBUG: AI processing completed")
            print(f"DEBUG: AI-generated name: {processed_data.get('name')}")
            print(f"DEBUG: AI-generated description: {processed_data.get('description', '')[:100]}...")
            print(f"DEBUG: AI-detected category: {processed_data.get('category')}")
            print(f"DEBUG: AI-detected features: {processed_data.get('key_features', [])}")
            
            # Step 3: Combine data
            final_data = {
                "name": processed_data.get("name", scraped_data.get("name", "Unknown Tool")),
                "description": processed_data.get("description", scraped_data.get("description", "")),
                "link": url,
                "logo_url": scraped_data.get("logo_url", ""),
                "category": processed_data.get("category", "Other"),
                "pricing_model": processed_data.get("pricing_model", "Unknown"),
                "key_features": json.dumps(processed_data.get("key_features", [])),
                "gallery_images": json.dumps([]),  # Empty for now
                "average_rating": 0,
                "total_ratings": 0,
                "is_featured": False,
                "submitter_email": email,
                "country_of_origin": country_of_origin,
                "status": "pending",  # pending, approved, rejected
                "created_at": datetime.now().isoformat()
            }
            
            print(f"DEBUG: Final tool data prepared for: {final_data['name']} from {country_of_origin}")
            
            return {
                "success": True,
                "data": final_data,
                "message": "Tool submitted successfully and is pending admin review."
            }
            
        except Exception as e:
            print(f"Error in submit_tool: {e}")
            return {"error": f"Submission failed: {str(e)}"}
        
    def _validate_groq_result(self, result: Dict[str, Any]) -> bool:
        """Validate that Groq result contains required fields with meaningful content"""
        required_fields = ['name', 'description', 'category', 'pricing_model', 'key_features']
        
        for field in required_fields:
            if field not in result:
                return False
            
            value = result[field]
            if field == 'key_features':
                if not isinstance(value, list) or len(value) == 0:
                    return False
            elif not value or (isinstance(value, str) and len(value.strip()) < 3):
                return False
        
        # Check for generic descriptions
        description = result.get('description', '').lower()
        generic_phrases = [
            'ai-powered tool for enhanced productivity',
            'artificial intelligence to streamline tasks',
            'utilizes artificial intelligence',
            'ai tool for productivity'
        ]
        
        if any(phrase in description for phrase in generic_phrases):
            return False
        
        return True

    def _create_intelligent_fallback(self, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create intelligent fallback data based on URL and scraped content"""
        url = scraped_data.get('link', '')
        name = scraped_data.get('name', 'Unknown Tool')
        description = scraped_data.get('description', '')
        content = scraped_data.get('scraped_content', '').lower()
        
        # Intelligent category detection based on URL and content
        category = self._detect_category(url, content)
        
        # Intelligent pricing model detection
        pricing_model = self._detect_pricing_model(content)
        
        # Generate features based on content analysis
        key_features = self._extract_features_from_content(content, url)
        
        # Clean up description or create a better one
        if len(description) < 50 or 'ai-powered tool for enhanced productivity' in description.lower():
            description = self._create_better_description(name, url, content, category)
        
        return {
            "name": name[:100],  # Limit length
            "description": description[:500],  # Limit length
            "category": category,
            "pricing_model": pricing_model,
            "key_features": key_features
        }

    def _detect_category(self, url: str, content: str) -> str:
        """Detect category based on URL and content"""
        url_lower = url.lower()
        content_lower = content.lower()
        
        # URL-based detection
        if any(term in url_lower for term in ['code', 'dev', 'github', 'coding', 'program']):
            return "Code & Development"
        elif any(term in url_lower for term in ['write', 'content', 'blog', 'article']):
            return "Writing & Content"
        elif any(term in url_lower for term in ['image', 'photo', 'pic', 'visual']):
            return "Image Generation"
        elif any(term in url_lower for term in ['video', 'movie', 'film']):
            return "Video Editing"
        elif any(term in url_lower for term in ['design', 'creative', 'art']):
            return "Design & Creative"
        elif any(term in url_lower for term in ['data', 'analytics', 'dashboard']):
            return "Data & Analytics"
        elif any(term in url_lower for term in ['business', 'finance', 'money']):
            return "Business & Finance"
        elif any(term in url_lower for term in ['learn', 'education', 'course', 'study']):
            return "Education & Learning"
        elif any(term in url_lower for term in ['chat', 'communication', 'message']):
            return "Communication"
        elif any(term in url_lower for term in ['music', 'audio', 'sound']):
            return "Audio & Music"
        elif any(term in url_lower for term in ['productivity', 'task', 'organize']):
            return "Productivity"
        elif any(term in url_lower for term in ['marketing', 'sales', 'campaign']):
            return "Marketing & Sales"
        
        # Content-based detection
        if any(term in content_lower for term in ['code', 'programming', 'developer', 'coding', 'software']):
            return "Code & Development"
        elif any(term in content_lower for term in ['writing', 'content creation', 'article', 'blog']):
            return "Writing & Content"
        elif any(term in content_lower for term in ['image generation', 'photo', 'pictures', 'visual']):
            return "Image Generation"
        elif any(term in content_lower for term in ['video editing', 'video creation', 'movie']):
            return "Video Editing"
        elif any(term in content_lower for term in ['design', 'creative', 'art', 'graphics']):
            return "Design & Creative"
        elif any(term in content_lower for term in ['data analysis', 'analytics', 'dashboard', 'metrics']):
            return "Data & Analytics"
        elif any(term in content_lower for term in ['business', 'finance', 'financial', 'money']):
            return "Business & Finance"
        elif any(term in content_lower for term in ['education', 'learning', 'course', 'study', 'teach']):
            return "Education & Learning"
        elif any(term in content_lower for term in ['chat', 'communication', 'messaging', 'conversation']):
            return "Communication"
        elif any(term in content_lower for term in ['music', 'audio', 'sound', 'voice']):
            return "Audio & Music"
        elif any(term in content_lower for term in ['productivity', 'task management', 'organize', 'workflow']):
            return "Productivity"
        elif any(term in content_lower for term in ['marketing', 'sales', 'campaign', 'promotion']):
            return "Marketing & Sales"
        
        return "Other"

    def _detect_pricing_model(self, content: str) -> str:
        """Detect pricing model from content"""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ['free forever', 'completely free', 'no cost', '100% free']):
            return "Free"
        elif any(term in content_lower for term in ['open source', 'github', 'open-source']):
            return "Open Source"
        elif any(term in content_lower for term in ['enterprise', 'custom pricing', 'contact sales']):
            return "Enterprise"
        elif any(term in content_lower for term in ['subscription', 'monthly', 'yearly', 'premium', 'pro plan']):
            return "Paid"
        elif any(term in content_lower for term in ['freemium', 'free trial', 'free plan', 'upgrade', 'limited free']):
            return "Freemium"
        
        return "Freemium"  # Default assumption

    def _extract_features_from_content(self, content: str, url: str) -> List[str]:
        """Extract potential features from content"""
        features = []
        content_lower = content.lower()
        
        # Common AI tool features
        if 'api' in content_lower:
            features.append("API Integration")
        if any(term in content_lower for term in ['automation', 'automatic']):
            features.append("Automation")
        if any(term in content_lower for term in ['real-time', 'realtime', 'live']):
            features.append("Real-time Processing")
        if any(term in content_lower for term in ['cloud', 'online']):
            features.append("Cloud-based")
        if any(term in content_lower for term in ['collaborative', 'team', 'share']):
            features.append("Collaboration")
        if any(term in content_lower for term in ['template', 'templates']):
            features.append("Templates")
        if any(term in content_lower for term in ['dashboard', 'analytics']):
            features.append("Analytics Dashboard")
        if any(term in content_lower for term in ['mobile', 'ios', 'android']):
            features.append("Mobile Support")
        if any(term in content_lower for term in ['integration', 'integrate', 'connect']):
            features.append("Third-party Integrations")
        if any(term in content_lower for term in ['ai', 'artificial intelligence', 'machine learning']):
            features.append("AI-powered")
        
        # If we don't have enough features, add some generic ones based on URL
        if len(features) < 3:
            domain_features = self._get_domain_based_features(url)
            features.extend(domain_features)
        
        # Limit to 5 features
        return features[:5] if features else ["AI-powered", "User-friendly", "Cloud-based"]

    def _get_domain_based_features(self, url: str) -> List[str]:
        """Get features based on domain analysis"""
        try:
            domain = urlparse(url).netloc.lower()
            if 'chat' in domain:
                return ["Conversational AI", "Natural Language Processing", "24/7 Availability"]
            elif 'code' in domain or 'dev' in domain:
                return ["Code Generation", "Syntax Highlighting", "Multiple Languages"]
            elif 'design' in domain:
                return ["Design Templates", "Visual Editor", "Creative Tools"]
            elif 'write' in domain:
                return ["Content Generation", "Grammar Check", "SEO Optimization"]
            else:
                return ["User-friendly Interface", "Fast Performance", "Reliable Service"]
        except:
            return ["User-friendly Interface", "Fast Performance", "Reliable Service"]

    def _create_better_description(self, name: str, url: str, content: str, category: str) -> str:
        """Create a better description based on available information"""
        try:
            domain = urlparse(url).netloc.replace('www.', '')
            
            category_descriptions = {
                "Code & Development": f"{name} is a development tool that helps developers write, test, and deploy code more efficiently.",
                "Writing & Content": f"{name} is a content creation platform that assists with writing, editing, and optimizing text.",
                "Image Generation": f"{name} is an AI-powered image generation tool that creates visual content from text descriptions.",
                "Video Editing": f"{name} provides video editing capabilities with AI-enhanced features for content creators.",
                "Design & Creative": f"{name} is a creative design tool that helps users create professional visual content.",
                "Data & Analytics": f"{name} offers data analysis and visualization tools for business insights.",
                "Business & Finance": f"{name} provides business solutions and financial tools for organizations.",
                "Education & Learning": f"{name} is an educational platform that enhances learning experiences.",
                "Communication": f"{name} facilitates communication and collaboration between users.",
                "Audio & Music": f"{name} provides audio processing and music creation capabilities.",
                "Productivity": f"{name} is a productivity tool that helps users manage tasks and optimize workflows.",
                "Marketing & Sales": f"{name} offers marketing automation and sales optimization features.",
                "Other": f"{name} is a specialized tool available at {domain} that provides unique AI-powered features."
            }
            
            base_description = category_descriptions.get(category, category_descriptions["Other"])
            
            # Add specific details if found in content
            if 'free' in content.lower():
                base_description += " Available with free access options."
            elif 'premium' in content.lower():
                base_description += " Offers premium features for advanced users."
            
            return base_description
            
        except:
            return f"{name} is an AI-powered tool that provides specialized features for enhanced productivity and efficiency."


def save_tool_submission(data: Dict[str, Any], db_conn) -> bool:
    """
    Save tool submission to database (pending admin approval)
    """
    try:
        # For Supabase
        if hasattr(db_conn, 'session'):  # Check if it's SupabaseConnection
            result = db_conn.insert('tool_submissions', data)
            return result.get('success', False)
        else:
            # For SQLite (fallback)
            cursor = db_conn.cursor()
              # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    link TEXT NOT NULL,
                    logo_url TEXT,
                    category TEXT NOT NULL,
                    pricing_model TEXT NOT NULL,
                    key_features TEXT,
                    gallery_images TEXT,
                    average_rating REAL DEFAULT 0,
                    total_ratings INTEGER DEFAULT 0,
                    is_featured BOOLEAN DEFAULT FALSE,
                    submitter_email TEXT NOT NULL,
                    country_of_origin TEXT NOT NULL DEFAULT 'Unknown',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert data
            placeholders = ', '.join(['?' for _ in data])
            columns = ', '.join(data.keys())
            values = list(data.values())
            
            cursor.execute(f"INSERT INTO tool_submissions ({columns}) VALUES ({placeholders})", values)
            db_conn.commit()
            return True
            
    except Exception as e:
        print(f"Error saving tool submission: {e}")
        return False

def get_pending_submissions(db_conn) -> List[Dict]:
    """
    Get all pending tool submissions for admin review
    """
    try:
        # For Supabase
        if hasattr(db_conn, 'session'):  # Check if it's SupabaseConnection
            result = db_conn.select('tool_submissions', '*', "status=eq.pending")
            return result.get('data', [])
        else:
            # For SQLite (fallback)
            cursor = db_conn.cursor()
            cursor.execute("SELECT * FROM tool_submissions WHERE status = 'pending' ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            # Convert to dict
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
    except Exception as e:
        print(f"Error getting pending submissions: {e}")
        return []

def approve_tool_submission(submission_id: int, db_conn) -> bool:
    """
    Approve a tool submission and move it to the main tools table
    """
    try:
        # Get submission data
        if hasattr(db_conn, 'session'):  # Check if it's SupabaseConnection
            result = db_conn.select('tool_submissions', '*', f"id=eq.{submission_id}")
            submission = result.get('data', [])
            if not submission:
                return False
            submission = submission[0]
        else:
            cursor = db_conn.cursor()
            cursor.execute("SELECT * FROM tool_submissions WHERE id = ?", (submission_id,))
            row = cursor.fetchone()
            if not row:
                return False
            columns = [description[0] for description in cursor.description]
            submission = dict(zip(columns, row))        # Check if tool with same URL already exists
        print(f"DEBUG: Checking for existing tool with URL: {submission['link']}")
        if hasattr(db_conn, 'session'):  # Check if it's SupabaseConnection
            try:
                # Use a direct query to check for existing tools
                import urllib.parse
                encoded_url = urllib.parse.quote(submission['link'], safe='')
                
                # Try a direct REST API call to check for duplicates
                import requests
                headers = db_conn.headers.copy()
                check_url = f"{db_conn.base_url}/rest/v1/tools?select=id&link=eq.{encoded_url}"
                
                response = requests.get(check_url, headers=headers)
                if response.status_code == 200:
                    existing_tools = response.json()
                    if existing_tools:
                        print(f"DEBUG: Tool with URL {submission['link']} already exists with ID: {existing_tools[0]['id']}")
                        return False
                    else:
                        print(f"DEBUG: No existing tool found with URL: {submission['link']}")
                else:
                    print(f"DEBUG: Failed to check for duplicates: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"DEBUG: Error checking for duplicates: {e}")
                # Continue with insert attempt
        else:
            cursor = db_conn.cursor()
            cursor.execute("SELECT id FROM tools WHERE link = ?", (submission['link'],))
            existing = cursor.fetchone()
            if existing:
                print(f"DEBUG: Tool with URL {submission['link']} already exists with ID: {existing[0]}")
                return False
          # Prepare data for tools table - only include fields that exist in tools table
        tool_data = {
            'name': submission['name'],
            'description': submission['description'],
            'link': submission['link'],
            'logo_url': submission.get('logo_url', ''),
            'category': submission['category'],
            'pricing_model': submission['pricing_model'],
            'average_rating': submission.get('average_rating', 0),
            'total_ratings': submission.get('total_ratings', 0),
            'key_features': submission.get('key_features', '[]'),
            'gallery_images': submission.get('gallery_images', '[]'),
            'country_of_origin': submission.get('country_of_origin', 'Unknown'),
            'is_featured': submission.get('is_featured', False)
            # Note: id, submitter_email, status, created_at are excluded
            # Note: featured_since will be set by database default (NULL)
        }
        
        # Double-check to ensure no id field is present
        if 'id' in tool_data:
            del tool_data['id']
            print("DEBUG: Removed id field from tool_data")
        
        print(f"DEBUG: Final tool_data keys: {list(tool_data.keys())}")
          # Insert into tools table
        if hasattr(db_conn, 'session'):  # Check if it's SupabaseConnection
            print(f"DEBUG: Inserting tool data: {tool_data}")
            result = db_conn.insert('tools', tool_data)
            success = result.get('success', False)
            if not success:
                print(f"DEBUG: Insert failed: {result}")
                error_msg = result.get('error', '')
                if '23505' in error_msg and 'tools_pkey' in error_msg:
                    print("DEBUG: This appears to be a primary key constraint violation")
                    print("DEBUG: This might mean the tool already exists. Treating as successful.")
                    # Treat this as success since the tool essentially exists
                    success = True
                elif 'duplicate key value violates unique constraint' in error_msg:
                    print("DEBUG: This appears to be a duplicate URL constraint violation")
                    print("DEBUG: Tool with this URL already exists. Treating as successful.")
                    success = True
                else:
                    print("DEBUG: This is a different type of error")
                    return False
            else:
                print("DEBUG: Insert successful")
        else:
            cursor = db_conn.cursor()
            placeholders = ', '.join(['?' for _ in tool_data])
            columns = ', '.join(tool_data.keys())
            values = list(tool_data.values())
            cursor.execute(f"INSERT INTO tools ({columns}) VALUES ({placeholders})", values)
            db_conn.commit()
            success = True
        
        # Always update submission status to approved if we got here
        print(f"DEBUG: Updating submission {submission_id} status to approved")
        if hasattr(db_conn, 'session'):  # Check if it's SupabaseConnection
            update_result = db_conn.update('tool_submissions', {'status': 'approved'}, f"id=eq.{submission_id}")
            print(f"DEBUG: Update submission result: {update_result}")
        else:
            cursor.execute("UPDATE tool_submissions SET status = 'approved' WHERE id = ?", (submission_id,))
            db_conn.commit()
        
        print(f"DEBUG: Returning success: {success}")
        return success
        
    except Exception as e:
        print(f"Error approving tool submission: {e}")
        return False

def reject_tool_submission(submission_id: int, db_conn) -> bool:
    """
    Reject a tool submission
    """
    try:
        if hasattr(db_conn, 'session'):  # Check if it's SupabaseConnection
            result = db_conn.update('tool_submissions', {'status': 'rejected'}, f"id=eq.{submission_id}")
            return result.get('success', False)
        else:
            cursor = db_conn.cursor()
            cursor.execute("UPDATE tool_submissions SET status = 'rejected' WHERE id = ?", (submission_id,))
            db_conn.commit()
            return True
            
    except Exception as e:
        print(f"Error rejecting tool submission: {e}")
        return False

    