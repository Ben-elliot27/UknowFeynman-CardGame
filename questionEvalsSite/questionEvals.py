# script.py
import json
import os
import uuid

from flask_socketio import emit


class QAManager:
    def __init__(self):
        script_dir = os.path.dirname(__file__)
        self.sources = {
            'main': str(os.path.join(script_dir, 'nlp_qa_pairs.json')),
            'simple': str(os.path.join(script_dir, 'evaluation_simple_qa_pairs.json'))
        }
        self.validated_files = {
            'main': str(os.path.join(script_dir, 'validated_qa_pairs_nlp.json')),
            'simple': str(os.path.join(script_dir, 'validated_qa_pairs_simple.json'))
        }
        self.votes_files = {
            'main': str(os.path.join(script_dir, 'votes_nlp.json')),
            'simple': str(os.path.join(script_dir, 'votes_simple.json'))
        }
        self.stats_files = {
            'main': str(os.path.join(script_dir, 'stats_nlp.json')),
            'simple': str(os.path.join(script_dir, 'stats_simple.json'))
        }
        self.REQUIRED_VOTES = 2
        self.init_files()

    def init_files(self):
        # Initialize all necessary files if they don't exist
        for file_dict in [self.validated_files, self.votes_files, self.stats_files]:
            for file_path in file_dict.values():
                if not os.path.exists(file_path):
                    self.save_json(file_path, {})

    def load_json(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_json(self, file_path, data):
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def ensure_qa_ids(self, tab):
        """Ensure all QA pairs have unique IDs and save back to source file"""
        source_file = self.sources[tab]
        try:
            with open(source_file, 'r') as f:
                qa_pairs = json.load(f)

            modified = False
            for qa in qa_pairs:
                if 'id' not in qa:
                    qa['id'] = str(uuid.uuid4())
                    modified = True

            if modified:
                self.save_json(source_file, qa_pairs)

            return qa_pairs
        except FileNotFoundError:
            return []

    def get_qa_pairs(self, tab):
        votes_file = self.votes_files[tab]
        votes = self.load_json(votes_file)

        # Get QA pairs and ensure they have IDs
        qa_pairs = self.ensure_qa_ids(tab)

        # Enhance QA pairs with voting data
        enhanced_pairs = []
        for qa in qa_pairs:
            qa_id = qa['id']
            if qa_id in votes:
                qa_with_votes = {
                    **qa,
                    'upvotes': len(votes[qa_id].get('upvotes', [])),
                    'downvotes': len(votes[qa_id].get('downvotes', []))
                }
                enhanced_pairs.append(qa_with_votes)
            else:
                enhanced_pairs.append({
                    **qa,
                    'upvotes': 0,
                    'downvotes': 0
                })

        return enhanced_pairs

    def handle_vote(self, data):
        tab = data['tab']
        qa_id = data['id']
        is_upvote = data['is_upvote']

        # Load current votes
        votes_file = self.votes_files[tab]
        votes = self.load_json(votes_file)

        # Initialize vote structure if needed
        if qa_id not in votes:
            votes[qa_id] = {'upvotes': [], 'downvotes': []}

        # Update votes
        vote_type = 'upvotes' if is_upvote else 'downvotes'
        votes[qa_id][vote_type].append(1)

        # Check if threshold reached
        upvotes = len(votes[qa_id]['upvotes'])
        downvotes = len(votes[qa_id]['downvotes'])
        should_remove = (upvotes >= self.REQUIRED_VOTES) or (downvotes >= self.REQUIRED_VOTES)

        # Handle removal if necessary
        if should_remove:
            source_file = self.sources[tab]
            qa_pairs = self.ensure_qa_ids(tab)

            # Find and remove the QA pair with matching ID
            removed_qa = None
            for i, qa in enumerate(qa_pairs):
                if qa['id'] == qa_id:
                    removed_qa = qa_pairs.pop(i)
                    break

            if removed_qa:
                self.save_json(source_file, qa_pairs)

                # If approved, save to validated file
                if upvotes >= self.REQUIRED_VOTES:
                    validated_file = self.validated_files[tab]
                    validated_pairs = self.load_json(validated_file)
                    validated_pairs[qa_id] = removed_qa
                    self.save_json(validated_file, validated_pairs)

                # Update statistics
                self.update_stats(tab, upvotes >= self.REQUIRED_VOTES)

        # Save updated votes
        self.save_json(votes_file, votes)

        return {
            'id': qa_id,
            'upvotes': upvotes,
            'downvotes': downvotes,
            'should_remove': should_remove
        }

    def update_stats(self, tab, is_approved):
        stats_file = self.stats_files[tab]
        stats = self.load_json(stats_file)

        if not stats:
            stats = {'approved': 0, 'rejected': 0, 'total_votes': 0}

        stats['total_votes'] += 1
        if is_approved:
            stats['approved'] += 1
        else:
            stats['rejected'] += 1

        self.save_json(stats_file, stats)
        return stats

    def get_stats(self, tab):
        stats_file = self.stats_files[tab]
        stats = self.load_json(stats_file)
        if not stats:
            stats = {'approved': 0, 'rejected': 0, 'total_votes': 0}
        return stats

def main(socketio):
    qa_manager = QAManager()

    @socketio.on('request_initial_data')
    def handle_initial_data_request(data):
        tab = data['tab']
        qa_pairs = qa_manager.get_qa_pairs(tab)
        emit('init_qa_pairs', {'qa_pairs': qa_pairs})

    @socketio.on('request_stats')
    def handle_stats_request(data):
        tab = data['tab']
        stats = qa_manager.get_stats(tab)
        emit('stats_update', stats)

    @socketio.on('vote')
    def handle_vote(data):
        result = qa_manager.handle_vote(data)
        emit('vote_update', result, broadcast=True)

        # Broadcast updated stats to all clients
        stats = qa_manager.get_stats(data['tab'])
        emit('stats_update', stats, broadcast=True)

    return "QA Ranking System Initialized"
