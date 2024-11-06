import React from 'react';

interface TextStatisticsProps {
  statistics: {
    word_count: number;
    sentence_count: number;
    unique_words: number;
    avg_sentence_length: number;
    most_common_words: [string, number][];
    top_scoring_words: [string, number][];
  };
}

export const TextStatistics: React.FC<TextStatisticsProps> = ({ statistics }) => {
  const formatNumber = (num: number) => {
    return num.toLocaleString('en-US', { maximumFractionDigits: 2 });
  };

  return (
    <div className="text-statistics">
      <div className="statistics-overview">
        <div className="stat-card total-words">
          <div className="stat-value">{formatNumber(statistics.word_count)}</div>
          <div className="stat-label">Total Words</div>
        </div>
        <div className="stat-card total-sentences">
          <div className="stat-value">{formatNumber(statistics.sentence_count)}</div>
          <div className="stat-label">Total Sentences</div>
        </div>
        <div className="stat-card unique-words">
          <div className="stat-value">{formatNumber(statistics.unique_words)}</div>
          <div className="stat-label">Unique Words</div>
        </div>
      </div>

      <div className="statistics-details">
        <div className="stat-table">
          <h3>Detailed Statistics</h3>
          <table>
            <tbody>
              <tr>
                <td>Vocabulary Density</td>
                <td>
                  {formatNumber((statistics.unique_words / statistics.word_count) * 100)}%
                </td>
              </tr>
              <tr>
                <td>Average Sentence Length</td>
                <td>{statistics.avg_sentence_length.toFixed(2)} words</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="common-words-section">
          <h3>Most Common Words</h3>
          <div className="common-words-grid">
            {statistics.most_common_words.map(([word, count], index) => (
              <div key={word} className="word-card">
                <span className="word-rank">#{index + 1}</span>
                <span className="word-text">{word}</span>
                <span className="word-frequency">
                  {count} time{count !== 1 ? 's' : ''}
                  <span className="frequency-percentage">
                    ({((count / statistics.word_count) * 100).toFixed(1)}%)
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>

        {statistics.top_scoring_words && statistics.top_scoring_words.length > 0 && (
          <div className="common-words-section">
            <h3>Top Scoring Words</h3>
            <div className="common-words-grid">
              {statistics.top_scoring_words.map(([word, score], index) => (
                <div key={word} className="word-card">
                  <span className="word-rank">#{index + 1}</span>
                  <span className="word-text">{word}</span>
                  <span className="word-frequency">
                    Score: {score.toFixed(3)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}; 