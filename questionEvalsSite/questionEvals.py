# script.py
import json
import os
import uuid

from flask_socketio import emit

class QAManager:
    def __init__(self):
        script_dir = os.path.dirname(__file__)
        self.sources = {
            'main': str(os.path.join(script_dir, 'questions', 'nlp_qa_pairs.json')),
            'simple': str(os.path.join(script_dir, 'questions', 'evaluation_simple_qa_pairs.json')),
            'mostViewed': str(os.path.join(script_dir, 'questions', 'MostViewedTwikis_qa.json')),
            'atlasTalk': str(os.path.join(script_dir, 'questions', 'AtlasTalk_qa.json'))
        }
        self.validated_files = {
            'main': str(os.path.join(script_dir, 'validated', 'validated_qa_pairs_nlp.json')),
            'simple': str(os.path.join(script_dir, 'validated', 'validated_qa_pairs_simple.json')),
            'mostViewed': str(os.path.join(script_dir, 'validated', 'validated_MostViewedTwikis.json')),
            'atlasTalk': str(os.path.join(script_dir, 'validated', 'validated_AtlasTalk.json'))
        }
        self.votes_files = {
            'main': str(os.path.join(script_dir, 'votes', 'votes_nlp.json')),
            'simple': str(os.path.join(script_dir, 'votes', 'votes_simple.json')),
            'mostViewed': str(os.path.join(script_dir, 'votes', 'MostViewedTwikis_votes.json')),
            'atlasTalk': str(os.path.join(script_dir, 'votes', 'AtlasTalk_votes.json'))
        }
        self.stats_files = {
            'main': str(os.path.join(script_dir, 'stats', 'stats_nlp.json')),
            'simple': str(os.path.join(script_dir, 'stats', 'stats_simple.json')),
            'mostViewed': str(os.path.join(script_dir, 'stats', 'stats_MostViewedTwikis.json')),
            'atlasTalk': str(os.path.join(script_dir, 'stats', 'stats_AtlasTalk.json'))
        }
        self.REQUIRED_VOTES = 2
        self.init_files()
        self.ITEMS_PER_PAGE = 30
        self.qa_cache = {}
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

    def get_qa_pairs(self, tab, page=0):
        """Get paginated QA pairs with voting data"""
        # Load or use cached QA pairs
        if tab not in self.qa_cache:
            qa_pairs = self.ensure_qa_ids(tab)
            votes = self.load_json(self.votes_files[tab])

            # Enhance QA pairs with voting data
            enhanced_pairs = []
            for qa in qa_pairs:
                qa_id = qa['id']
                qa_with_votes = {
                    **qa,
                    'upvotes': len(votes.get(qa_id, {}).get('upvotes', [])),
                    'downvotes': len(votes.get(qa_id, {}).get('downvotes', []))
                }
                enhanced_pairs.append(qa_with_votes)

            self.qa_cache[tab] = enhanced_pairs

        # Calculate pagination
        start_idx = page * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        total_items = len(self.qa_cache[tab])
        total_pages = (total_items + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE

        return {
            'items': self.qa_cache[tab][start_idx:end_idx],
            'total_pages': total_pages,
            'current_page': page,
            'total_items': total_items
        }

    def handle_vote(self, data):
        tab = data['tab']
        qa_id = data['id']
        is_upvote = data['is_upvote']

        # Clear cache for this tab since votes are changing
        if tab in self.qa_cache:
            del self.qa_cache[tab]

        # Rest of the existing vote handling code...
        votes = self.load_json(self.votes_files[tab])

        if qa_id not in votes:
            votes[qa_id] = {'upvotes': [], 'downvotes': []}

        vote_type = 'upvotes' if is_upvote else 'downvotes'
        votes[qa_id][vote_type].append(1)

        upvotes = len(votes[qa_id]['upvotes'])
        downvotes = len(votes[qa_id]['downvotes'])
        should_remove = (upvotes >= self.REQUIRED_VOTES) or (downvotes >= self.REQUIRED_VOTES)
        self.update_stats(tab, "NA")

        if should_remove:
            source_file = self.sources[tab]
            qa_pairs = self.ensure_qa_ids(tab)

            removed_qa = None
            for i, qa in enumerate(qa_pairs):
                if qa['id'] == qa_id:
                    removed_qa = qa_pairs.pop(i)
                    break

            if removed_qa:
                self.save_json(source_file, qa_pairs)

                if upvotes >= self.REQUIRED_VOTES:
                    validated_file = self.validated_files[tab]
                    validated_pairs = self.load_json(validated_file)
                    validated_pairs[qa_id] = removed_qa
                    self.save_json(validated_file, validated_pairs)

                self.update_stats(tab, upvotes >= self.REQUIRED_VOTES)

        self.save_json(self.votes_files[tab], votes)

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


        if is_approved == "NA":
            stats['total_votes'] += 1
        elif is_approved:
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
        page = data.get('page', 0)
        try:
            qa_data = qa_manager.get_qa_pairs(tab, page)
        except KeyError:
            emit('error', {'message': 'Invalid tab specified'})
            return
        emit('init_qa_pairs', qa_data)

    @socketio.on('request_stats')
    def handle_stats_request(data):
        tab = data['tab']
        try:
            stats = qa_manager.get_stats(tab)
        except KeyError:
            emit('error', {'message': 'Invalid tab specified'})
            return
        emit('stats_update', stats)

    @socketio.on('vote')
    def handle_vote(data):
        try:
            result = qa_manager.handle_vote(data)
            emit('vote_update', result, broadcast=True)

            # Broadcast updated stats to all clients
            stats = qa_manager.get_stats(data['tab'])
            emit('stats_update', stats, broadcast=True)
        except Exception as e:
            emit('error', {'message': f'Error: {e}'})

    return "QA Ranking System Initialized"
