"""
Investigative Agent Framework
Orchestrates multi-model agent execution for investigative tasks
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime


class InvestigativeAgent:
    """Execute investigative tasks using multiple models"""
    
    def __init__(self, agent_type: str, models: List[str]):
        self.agent_type = agent_type
        self.models = models
        self.execution_log = []
    
    async def execute(self, task: str, parameters: Dict) -> Dict:
        """Execute an investigative task"""
        start_time = datetime.now()
        
        result = {
            "agent_type": self.agent_type,
            "task": task,
            "models": self.models,
            "status": "completed",
            "start_time": start_time.isoformat(),
            "steps": [],
            "output": None
        }
        
        try:
            if self.agent_type == "research":
                output = await self._research_agent(task, parameters)
            elif self.agent_type == "analysis":
                output = await self._analysis_agent(task, parameters)
            elif self.agent_type == "summary":
                output = await self._summary_agent(task, parameters)
            elif self.agent_type == "investigation":
                output = await self._investigation_agent(task, parameters)
            else:
                output = f"Unknown agent type: {self.agent_type}"
            
            result["output"] = output
            result["execution_log"] = self.execution_log
        
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
        
        end_time = datetime.now()
        result["end_time"] = end_time.isoformat()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
        return result
    
    async def _research_agent(self, task: str, parameters: Dict) -> str:
        """Research agent - gathers information"""
        self._log_step("Starting research agent")
        
        # Simulate multi-model research
        outputs = []
        for model in self.models:
            self._log_step(f"Querying model: {model}")
            # In real implementation, this would call the model
            outputs.append(f"[{model}] Research on: {task}")
        
        result = "\n\n".join(outputs)
        self._log_step("Research completed")
        return result
    
    async def _analysis_agent(self, task: str, parameters: Dict) -> str:
        """Analysis agent - analyzes data"""
        self._log_step("Starting analysis agent")
        
        data = parameters.get("data", "")
        
        outputs = []
        for model in self.models:
            self._log_step(f"Analyzing with model: {model}")
            outputs.append(f"[{model}] Analysis of: {task}\nData: {data[:100]}...")
        
        result = "\n\n".join(outputs)
        self._log_step("Analysis completed")
        return result
    
    async def _summary_agent(self, task: str, parameters: Dict) -> str:
        """Summary agent - summarizes content"""
        self._log_step("Starting summary agent")
        
        content = parameters.get("content", "")
        
        # Use first model for summary
        model = self.models[0] if self.models else "default"
        self._log_step(f"Generating summary with model: {model}")
        
        result = f"[{model}] Summary of: {task}\nContent length: {len(content)} characters"
        self._log_step("Summary completed")
        return result
    
    async def _investigation_agent(self, task: str, parameters: Dict) -> str:
        """Investigation agent - multi-step investigation"""
        self._log_step("Starting investigation agent")
        
        # Step 1: Gather information
        self._log_step("Step 1: Information gathering")
        info = f"Gathering information about: {task}"
        
        # Step 2: Analyze findings
        self._log_step("Step 2: Analysis")
        analysis = f"Analyzing findings for: {task}"
        
        # Step 3: Cross-reference
        self._log_step("Step 3: Cross-referencing")
        cross_ref = "Cross-referencing data across sources"
        
        # Step 4: Generate report
        self._log_step("Step 4: Report generation")
        report = f"""
INVESTIGATION REPORT
====================
Task: {task}
Models Used: {', '.join(self.models)}

1. Information Gathering:
{info}

2. Analysis:
{analysis}

3. Cross-Reference:
{cross_ref}

4. Conclusion:
Investigation completed. See detailed findings above.
"""
        
        self._log_step("Investigation completed")
        return report
    
    def _log_step(self, message: str):
        """Log an execution step"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        self.execution_log.append(log_entry)
