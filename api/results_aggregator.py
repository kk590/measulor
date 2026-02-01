"""Tool 6: Results Aggregator
Aggregates and analyzes results from video processing pipeline
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json

class ResultsAggregator:
    """Aggregates and analyzes video measurement results"""
    
    def __init__(self):
        self.results = {
            'video_info': {},
            'processing_stats': {},
            'measurements': {},
            'quality_analysis': {},
            'timestamp': None
        }
    
    def aggregate_results(self, 
                         video_info: Dict,
                         frames: List,
                         poses: List[Dict],
                         validation_results: Dict,
                         measurements: Dict) -> Dict:
        """
        Aggregate all results from the processing pipeline
        
        Args:
            video_info: Video metadata
            frames: Extracted frames
            poses: Detected poses
            validation_results: Quality validation results
            measurements: Calculated measurements
        
        Returns:
            Complete aggregated results
        """
        self.results['timestamp'] = datetime.now().isoformat()
        
        # Video information
        self.results['video_info'] = {
            'filename': video_info.get('filename'),
            'duration': video_info.get('duration'),
            'fps': video_info.get('fps'),
            'total_frames': video_info.get('frame_count')
        }
        
        # Processing statistics
        self.results['processing_stats'] = {
            'frames_extracted': len(frames),
            'frames_analyzed': len(poses),
            'valid_frames': validation_results.get('valid_frames', 0),
            'invalid_frames': validation_results.get('invalid_frames', 0),
            'valid_percentage': validation_results.get('valid_percentage', 0),
            'frames_used_for_measurement': measurements.get('frames_used', 0)
        }
        
        # Measurements
        self.results['measurements'] = measurements
        
        # Quality analysis
        self.results['quality_analysis'] = self._analyze_quality(
            validation_results,
            measurements
        )
        
        return self.results
    
    def _analyze_quality(self, validation_results: Dict, measurements: Dict) -> Dict:
        """
        Analyze overall quality of the measurements
        
        Args:
            validation_results: Validation results
            measurements: Measurement results
        
        Returns:
            Quality analysis
        """
        quality = {}
        
        # Overall quality score based on valid frames percentage
        valid_percentage = validation_results.get('valid_percentage', 0)
        
        if valid_percentage >= 80:
            quality['overall_quality'] = 'excellent'
            quality['confidence'] = 'high'
        elif valid_percentage >= 60:
            quality['overall_quality'] = 'good'
            quality['confidence'] = 'medium'
        elif valid_percentage >= 40:
            quality['overall_quality'] = 'fair'
            quality['confidence'] = 'medium'
        else:
            quality['overall_quality'] = 'poor'
            quality['confidence'] = 'low'
        
        quality['valid_frame_percentage'] = valid_percentage
        
        # Check measurement consistency (using standard deviations)
        std_keys = [k for k in measurements.keys() if k.endswith('_std')]
        if std_keys:
            avg_std = np.mean([measurements[k] for k in std_keys if isinstance(measurements.get(k), (int, float))])
            quality['measurement_consistency'] = 'high' if avg_std < 2 else ('medium' if avg_std < 5 else 'low')
        else:
            quality['measurement_consistency'] = 'unknown'
        
        # Recommendations
        quality['recommendations'] = self._generate_recommendations(valid_percentage, quality)
        
        return quality
    
    def _generate_recommendations(self, valid_percentage: float, quality: Dict) -> List[str]:
        """
        Generate recommendations based on quality analysis
        
        Args:
            valid_percentage: Percentage of valid frames
            quality: Quality metrics
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if valid_percentage < 50:
            recommendations.append("Consider recording a new video with better lighting and visibility")
            recommendations.append("Ensure the full body is visible in the frame")
        
        if quality.get('measurement_consistency') == 'low':
            recommendations.append("Results show high variance - consider taking multiple measurements")
            recommendations.append("Try to maintain a stable position during recording")
        
        if quality.get('confidence') == 'low':
            recommendations.append("Low confidence in measurements - retake video recommended")
        
        if not recommendations:
            recommendations.append("Measurements appear reliable - no issues detected")
        
        return recommendations
    
    def get_summary(self) -> Dict:
        """
        Get a concise summary of results
        
        Returns:
            Summary dictionary
        """
        if not self.results.get('measurements'):
            return {'error': 'No results to summarize'}
        
        summary = {
            'timestamp': self.results['timestamp'],
            'video': self.results['video_info'].get('filename'),
            'quality': self.results['quality_analysis'].get('overall_quality'),
            'confidence': self.results['quality_analysis'].get('confidence'),
            'frames_analyzed': self.results['processing_stats'].get('frames_analyzed'),
            'valid_frames': self.results['processing_stats'].get('valid_frames'),
            'key_measurements': {}
        }
        
        # Extract key measurements
        measurements = self.results['measurements']
        key_fields = ['height', 'shoulder_width', 'arm_length', 'torso_length', 'leg_length', 'hip_width', 'inseam']
        
        for field in key_fields:
            if field in measurements:
                value = measurements[field]
                unit = measurements.get('unit', 'pixels')
                summary['key_measurements'][field] = f"{value:.2f} {unit}"
        
        return summary
    
    def export_json(self) -> str:
        """
        Export results as JSON string
        
        Returns:
            JSON string of results
        """
        return json.dumps(self.results, indent=2, default=str)
    
    def export_formatted_report(self) -> str:
        """
        Export results as formatted text report
        
        Returns:
            Formatted text report
        """
        if not self.results.get('measurements'):
            return "No results available"
        
        report = []
        report.append("=" * 50)
        report.append("BODY MEASUREMENT REPORT")
        report.append("=" * 50)
        report.append(f"\nTimestamp: {self.results['timestamp']}")
        report.append(f"Video: {self.results['video_info'].get('filename')}\n")
        
        # Processing Stats
        report.append("Processing Statistics:")
        report.append("-" * 50)
        stats = self.results['processing_stats']
        report.append(f"  Frames Extracted: {stats.get('frames_extracted')}")
        report.append(f"  Frames Analyzed: {stats.get('frames_analyzed')}")
        report.append(f"  Valid Frames: {stats.get('valid_frames')} ({stats.get('valid_percentage', 0):.1f}%)")
        report.append(f"  Used for Measurement: {stats.get('frames_used_for_measurement')}\n")
        
        # Quality Analysis
        report.append("Quality Analysis:")
        report.append("-" * 50)
        quality = self.results['quality_analysis']
        report.append(f"  Overall Quality: {quality.get('overall_quality', 'unknown').upper()}")
        report.append(f"  Confidence: {quality.get('confidence', 'unknown').upper()}")
        report.append(f"  Measurement Consistency: {quality.get('measurement_consistency', 'unknown').upper()}\n")
        
        # Measurements
        report.append("Body Measurements:")
        report.append("-" * 50)
        measurements = self.results['measurements']
        unit = measurements.get('unit', 'pixels')
        
        key_measurements = [
            ('Height', 'height'),
            ('Shoulder Width', 'shoulder_width'),
            ('Arm Length', 'arm_length'),
            ('Torso Length', 'torso_length'),
            ('Hip Width', 'hip_width'),
            ('Leg Length', 'leg_length'),
            ('Inseam', 'inseam')
        ]
        
        for label, key in key_measurements:
            if key in measurements:
                value = measurements[key]
                std = measurements.get(f'{key}_std', 0)
                report.append(f"  {label}: {value:.2f} ± {std:.2f} {unit}")
        
        report.append("\nRecommendations:")
        report.append("-" * 50)
        for rec in quality.get('recommendations', []):
            report.append(f"  • {rec}")
        
        report.append("\n" + "=" * 50)
        
        return "\n".join(report)

def aggregate_pipeline_results(video_info: Dict,
                               frames: List,
                               poses: List[Dict],
                               validation_results: Dict,
                               measurements: Dict) -> Tuple[bool, any]:
    """
    Convenience function to aggregate all pipeline results
    
    Args:
        video_info: Video metadata
        frames: Extracted frames
        poses: Detected poses
        validation_results: Quality validation results
        measurements: Calculated measurements
    
    Returns:
        (success, aggregated_results or error_message)
    """
    try:
        aggregator = ResultsAggregator()
        results = aggregator.aggregate_results(
            video_info,
            frames,
            poses,
            validation_results,
            measurements
        )
        return True, results
    except Exception as e:
        return False, f"Results aggregation error: {str(e)}"
