/**
 * Copies text to the clipboard using the modern Clipboard API if available,
 * with a fallback to a temporary textarea and document.execCommand('copy').
 * 
 * @param {string} text - The text to copy to the clipboard.
 * @returns {Promise<boolean>} - Resolves to true if the copy was successful, false otherwise.
 */
export const copyToClipboard = async (text) => {
  if (!text) return false;

  // Try the modern Clipboard API first
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn('Clipboard API failed, falling back to execCommand', err);
    }
  }

  // Fallback to execCommand('copy')
  try {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    
    // Ensure the textarea is not visible but part of the DOM
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    textArea.style.top = '0';
    document.body.appendChild(textArea);
    
    textArea.focus();
    textArea.select();
    
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    
    return successful;
  } catch (err) {
    console.error('Fallback copy failed', err);
    return false;
  }
};
