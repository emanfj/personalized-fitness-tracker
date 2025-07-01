# adaptive_agent.py
import json
import redis
from datetime import datetime, timedelta
from pymongo import MongoClient
from plan_generator import call_llm

redis_client = redis.Redis(host="localhost", port=6379, db=0)
mongo = MongoClient("mongodb://localhost:27017").fitness_tracker

class AdaptiveAgent:
    def __init__(self):
        self.adaptation_thresholds = {
            'low_completion_rate': 0.6,
            'high_difficulty_rating': 8.0,
            'low_satisfaction': 5.0,
            'consecutive_missed_days': 3,
            'poor_performance_trend': 0.7  # compared to previous week
        }
    
    def check_adaptation_needed(self, user_id: str) -> list:
        """
        Check if user needs workout adaptation based on recent performance
        Returns list of adaptation reasons
        """
        adaptations_needed = []
        
        # Get recent performance data
        recent_data = self.get_recent_performance(user_id, days=7)
        
        # Check completion rate
        if recent_data['completion_rate'] < self.adaptation_thresholds['low_completion_rate']:
            adaptations_needed.append('reduce_difficulty')
        
        # Check difficulty feedback
        if recent_data['avg_difficulty_rating'] > self.adaptation_thresholds['high_difficulty_rating']:
            adaptations_needed.append('make_easier')
        
        # Check satisfaction
        if recent_data['avg_satisfaction'] < self.adaptation_thresholds['low_satisfaction']:
            adaptations_needed.append('change_variety')
        
        # Check consecutive missed days
        if recent_data['consecutive_missed'] >= self.adaptation_thresholds['consecutive_missed_days']:
            adaptations_needed.append('reduce_frequency')
        
        # Check performance trend
        if recent_data['performance_trend'] < self.adaptation_thresholds['poor_performance_trend']:
            adaptations_needed.append('adjust_intensity')
        
        return adaptations_needed
    
    def get_recent_performance(self, user_id: str, days: int = 7) -> dict:
        """
        Aggregate recent performance metrics from your existing data
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get feedback data
        feedback_data = list(mongo.fitness_feedback.find({
            "user_id": user_id,
            "feedback_ts": {"$gte": start_date, "$lte": end_date}
        }))
        
        # Get workout completion data
        workout_data = list(mongo.fitness_events.find({
            "user_id": user_id,
            "event_type": "workout_completed",
            "event_ts": {"$gte": start_date, "$lte": end_date}
        }))
        
        # Calculate metrics
        total_workouts_planned = days  # Assuming 1 workout per day
        completed_workouts = len(workout_data)
        completion_rate = completed_workouts / total_workouts_planned if total_workouts_planned > 0 else 0
        
        avg_difficulty_rating = sum(f.get('difficulty_rating', 5) for f in feedback_data) / len(feedback_data) if feedback_data else 5
        avg_satisfaction = sum(f.get('satisfaction_rating', 5) for f in feedback_data) / len(feedback_data) if feedback_data else 5
        
        # Calculate consecutive missed days
        consecutive_missed = self.calculate_consecutive_missed(user_id)
        
        # Calculate performance trend (simplified)
        performance_trend = self.calculate_performance_trend(user_id, days)
        
        return {
            'completion_rate': completion_rate,
            'avg_difficulty_rating': avg_difficulty_rating,
            'avg_satisfaction': avg_satisfaction,
            'consecutive_missed': consecutive_missed,
            'performance_trend': performance_trend,
            'total_feedback_entries': len(feedback_data)
        }
    
    def calculate_consecutive_missed(self, user_id: str) -> int:
        """Calculate consecutive missed workout days"""
        recent_completions = list(mongo.fitness_events.find({
            "user_id": user_id,
            "event_type": "workout_completed"
        }).sort("event_ts", -1).limit(7))
        
        if not recent_completions:
            return 7
        
        last_completion = recent_completions[0]['event_ts']
        days_since_last = (datetime.utcnow() - last_completion).days
        return min(days_since_last, 7)
    
    def calculate_performance_trend(self, user_id: str, days: int) -> float:
        """Compare current week performance to previous week"""
        current_week = self.get_recent_performance(user_id, days)
        previous_week = self.get_recent_performance_offset(user_id, days, days)
        
        if previous_week['completion_rate'] == 0:
            return 1.0
        
        return current_week['completion_rate'] / previous_week['completion_rate']
    
    def get_recent_performance_offset(self, user_id: str, days: int, offset: int) -> dict:
        """Get performance data for a previous time period"""
        end_date = datetime.utcnow() - timedelta(days=offset)
        start_date = end_date - timedelta(days=days)
        
        workout_data = list(mongo.fitness_events.find({
            "user_id": user_id,
            "event_type": "workout_completed",
            "event_ts": {"$gte": start_date, "$lte": end_date}
        }))
        
        completion_rate = len(workout_data) / days if days > 0 else 0
        return {'completion_rate': completion_rate}
    
    def adapt_workout_plan(self, user_id: str, current_plan: dict, adaptations: list) -> dict:
        """
        Use LLM to adapt the workout plan based on identified issues
        """
        adaptation_context = {
            'current_plan': current_plan,
            'adaptations_needed': adaptations,
            'user_performance': self.get_recent_performance(user_id)
        }
        
        prompt = self.build_adaptation_prompt(adaptation_context)
        
        try:
            adapted_plan_raw = call_llm(prompt, model="llama3.2:3b")
            adapted_plan = json.loads(adapted_plan_raw)
            
            # Log the adaptation
            self.log_adaptation(user_id, adaptations, adapted_plan)
            
            return adapted_plan
        except Exception as e:
            print(f"LLM adaptation failed: {e}")
            # Fallback to rule-based adaptation
            return self.rule_based_adaptation(current_plan, adaptations)
    
    def build_adaptation_prompt(self, ctx: dict) -> str:
        """Build prompt for LLM to adapt workout plan"""
        return f"""
You are an expert personal trainer making real-time adjustments to a workout plan.

CURRENT WORKOUT PLAN:
{json.dumps(ctx['current_plan'], indent=2)}

USER PERFORMANCE ISSUES:
{', '.join(ctx['adaptations_needed'])}

PERFORMANCE METRICS:
- Completion Rate: {ctx['user_performance']['completion_rate']:.1%}
- Average Difficulty Rating: {ctx['user_performance']['avg_difficulty_rating']:.1}/10
- Average Satisfaction: {ctx['user_performance']['avg_satisfaction']:.1}/10
- Consecutive Missed Days: {ctx['user_performance']['consecutive_missed']}

ADAPTATION INSTRUCTIONS:
{self.get_adaptation_instructions(ctx['adaptations_needed'])}

Return the adapted workout plan in the EXACT same JSON format as the current plan, but with appropriate modifications to address the performance issues.
"""
    
    def get_adaptation_instructions(self, adaptations: list) -> str:
        """Get specific instructions for each adaptation type"""
        instructions = []
        
        for adaptation in adaptations:
            if adaptation == 'reduce_difficulty':
                instructions.append("- Reduce sets by 1 or reps by 20-30%")
            elif adaptation == 'make_easier':
                instructions.append("- Replace complex exercises with simpler variants")
            elif adaptation == 'change_variety':
                instructions.append("- Swap 2-3 exercises for different ones targeting same muscles")
            elif adaptation == 'reduce_frequency':
                instructions.append("- Add more rest days or reduce workout duration")
            elif adaptation == 'adjust_intensity':
                instructions.append("- Lower intensity by reducing weight/speed recommendations")
        
        return '\n'.join(instructions)
    
    def rule_based_adaptation(self, current_plan: dict, adaptations: list) -> dict:
        """Fallback rule-based adaptation if LLM fails"""
        adapted_plan = current_plan.copy()
        
        for adaptation in adaptations:
            if adaptation == 'reduce_difficulty':
                # Reduce sets/reps by 20%
                for day in adapted_plan.get('days', []):
                    for exercise in day.get('exercises', []):
                        if 'sets' in exercise:
                            exercise['sets'] = max(1, int(exercise['sets'] * 0.8))
                        if 'reps' in exercise:
                            exercise['reps'] = max(5, int(exercise['reps'] * 0.8))
        
        return adapted_plan
    
    def log_adaptation(self, user_id: str, adaptations: list, adapted_plan: dict):
        """Log adaptation for analysis"""
        mongo.plan_adaptations.insert_one({
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'adaptations_applied': adaptations,
            'adapted_plan': adapted_plan
        })

