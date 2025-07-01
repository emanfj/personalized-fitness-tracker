# real_time_monitor.py
import threading
import time
from adaptive_agent import AdaptiveAgent

class RealTimeMonitor:
    def __init__(self):
        self.agent = AdaptiveAgent()
        self.monitoring = False
        
    def start_monitoring(self):
        """Start the real-time monitoring thread"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        print("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring"""
        self.monitoring = False
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Get all active users
                active_users = self.get_active_users()
                
                for user_id in active_users:
                    self.check_user_adaptation(user_id)
                
                # Sleep for 1 hour before next check
                time.sleep(3600)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def get_active_users(self) -> list:
        """Get list of active users to monitor"""
        # Get users who have been active in the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        active_users = mongo.fitness_events.distinct("user_id", {
            "event_ts": {"$gte": yesterday}
        })
        return active_users
    
    def check_user_adaptation(self, user_id: str):
        """Check if a specific user needs adaptation"""
        adaptations_needed = self.agent.check_adaptation_needed(user_id)
        
        if adaptations_needed:
            print(f"User {user_id} needs adaptations: {adaptations_needed}")
            
            # Get current plan
            current_plan = self.get_current_plan(user_id)
            
            if current_plan:
                # Adapt the plan
                adapted_plan = self.agent.adapt_workout_plan(
                    user_id, current_plan, adaptations_needed
                )
                
                # Update the plan in database
                self.update_user_plan(user_id, adapted_plan)
                
                # Notify user
                self.notify_user_adaptation(user_id, adaptations_needed)
    
    def get_current_plan(self, user_id: str) -> dict:
        """Get user's current workout plan"""
        plan = mongo.workout_plans.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )
        return plan.get('plan', {}) if plan else {}
    
    def update_user_plan(self, user_id: str, adapted_plan: dict):
        """Update user's workout plan"""
        mongo.workout_plans.insert_one({
            'user_id': user_id,
            'plan': adapted_plan,
            'created_at': datetime.utcnow(),
            'adapted': True
        })
    
    def notify_user_adaptation(self, user_id: str, adaptations: list):
        """Notify user about plan adaptation"""
        # This could send push notification, email, etc.
        print(f"Notifying user {user_id} about adaptations: {adaptations}")


# Updated app.py - Add these endpoints
from real_time_monitor import RealTimeMonitor

# Initialize monitor
monitor = RealTimeMonitor()

@app.on_event("startup")
async def startup_event():
    """Start monitoring when app starts"""
    monitor.start_monitoring()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop monitoring when app shuts down"""
    monitor.stop_monitoring()

@app.post("/feedback/{user_id}")
def submit_feedback(user_id: str, feedback: dict):
    """
    Submit user feedback and trigger immediate adaptation check
    """
    # Store feedback in MongoDB
    mongo.fitness_feedback.insert_one({
        'user_id': user_id,
        'feedback_ts': datetime.utcnow(),
        'difficulty_rating': feedback.get('difficulty_rating', 5),
        'satisfaction_rating': feedback.get('satisfaction_rating', 5),
        'completion_status': feedback.get('completed', True),
        'notes': feedback.get('notes', '')
    })
    
    # Trigger immediate adaptation check
    adaptations_needed = monitor.agent.check_adaptation_needed(user_id)
    
    if adaptations_needed:
        current_plan = monitor.get_current_plan(user_id)
        if current_plan:
            adapted_plan = monitor.agent.adapt_workout_plan(
                user_id, current_plan, adaptations_needed
            )
            monitor.update_user_plan(user_id, adapted_plan)
            
            return {
                "message": "Plan adapted based on feedback",
                "adaptations": adaptations_needed,
                "new_plan": adapted_plan
            }
    
    return {"message": "Feedback received"}

@app.get("/adaptation-status/{user_id}")
def get_adaptation_status(user_id: str):
    """
    Get user's adaptation status and recent changes
    """
    recent_adaptations = list(mongo.plan_adaptations.find({
        "user_id": user_id
    }).sort("timestamp", -1).limit(5))
    
    performance = monitor.agent.get_recent_performance(user_id)
    
    return {
        "user_id": user_id,
        "recent_adaptations": recent_adaptations,
        "current_performance": performance,
        "adaptation_needed": monitor.agent.check_adaptation_needed(user_id)
    }