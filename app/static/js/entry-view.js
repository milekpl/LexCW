/**
 * Lexicographic Curation Workbench - Entry View JavaScript
 * 
 * This file contains the functionality for the entry view page.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize audio player modal
    const audioPlayerModal = new bootstrap.Modal(document.getElementById('audioPlayerModal'));
    const audioPlayer = document.getElementById('audio-player');
    
    // Handle play audio buttons
    document.querySelectorAll('.play-audio-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const audioFile = this.dataset.audioFile;
            if (audioFile) {
                // Set the audio source
                audioPlayer.src = `/audio/${audioFile}`;
                
                // Show the modal
                audioPlayerModal.show();
                
                // Play the audio
                audioPlayer.play();
            }
        });
    });
    
    // When modal is hidden, pause the audio
    document.getElementById('audioPlayerModal').addEventListener('hidden.bs.modal', function() {
        audioPlayer.pause();
    });
});
