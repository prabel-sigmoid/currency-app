import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Calendar, Download, AlertCircle, CheckCircle, Loader, Upload, Database } from 'lucide-react';

// Use window.location to determine API URL
const API_BASE_URL = "/api"; 

export default function CurrencyAnalyzer() {
  const [currencies, setCurrencies] = useState({});
  const [selectedCurrencies, setSelectedCurrencies] = useState(['INR', 'MXN', 'JPY']);
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setFullYear(date.getFullYear() - 1);
    return date.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate());
    return date.toISOString().split('T')[0];
  });
  const [interval, setInterval] = useState('1mo');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [dataSource, setDataSource] = useState('api');
  const [csvFile, setCsvFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [dateAdjusted, setDateAdjusted] = useState(false);

  useEffect(() => {
    console.log('API Base URL:', API_BASE_URL);
    fetch(`${API_BASE_URL}/currencies`)
      .then(res => res.json())
      .then(data => setCurrencies(data.currencies))
      .catch(err => {
        console.error('Error fetching currencies:', err);
        setError('Failed to connect to backend API');
      });
  }, []);

  const handleCurrencyToggle = (currency) => {
    setSelectedCurrencies(prev => 
      prev.includes(currency) 
        ? prev.filter(c => c !== currency)
        : [...prev, currency]
    );
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        setError('Please upload a CSV file');
        return;
      }
      setCsvFile(file);
      setError(null);
      setUploadStatus(null);
    }
  };

  const handleAnalyze = async () => {
    if (selectedCurrencies.length === 0) {
      setError('Please select at least one currency');
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);
    setUploadStatus(null);
    setDateAdjusted(false);

    try {
      if (dataSource === 'api') {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const selectedEnd = new Date(endDate);
        
        if (selectedEnd > today) {
          setDateAdjusted(true);
        }
        
        const response = await fetch(`${API_BASE_URL}/exchange-rates`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            currencies: selectedCurrencies,
            start_date: startDate,
            end_date: endDate,
            interval: interval
          })
        });

        const result = await response.json();
        
        if (response.ok && result.data && result.data.length > 0) {
          setData(result);
        } else {
          setError(result.message || 'No data available');
        }
      } else {
        if (!csvFile) {
          setError('Please select a CSV file to upload');
          setLoading(false);
          return;
        }

        const formData = new FormData();
        formData.append('file', csvFile);
        formData.append('currencies', selectedCurrencies.join(','));
        formData.append('start_date', startDate);
        formData.append('end_date', endDate);
        formData.append('interval', interval);

        const response = await fetch(`${API_BASE_URL}/analyze-csv`, {
          method: 'POST',
          body: formData
        });

        const result = await response.json();
        
        if (response.ok && result.data && result.data.length > 0) {
          setData(result);
          setUploadStatus('CSV data analyzed and stored in database successfully!');
        } else {
          setError(result.detail || result.message || 'Failed to analyze CSV');
        }
      }
    } catch (err) {
      setError(`Failed to connect to API at ${API_BASE_URL}. Make sure the backend is running.`);
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/download-template`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'exchange_rates_template.csv';
      a.click();
    } catch (err) {
      console.error('Error downloading template:', err);
    }
  };

  const formatChartData = () => {
    if (!data || !data.data) return [];
    
    const dateMap = new Map();
    
    data.data.forEach(currency => {
      currency.dates.forEach((date, idx) => {
        if (!dateMap.has(date)) {
          dateMap.set(date, { date });
        }
        dateMap.get(date)[currency.currency] = currency.rates[idx];
      });
    });
    
    return Array.from(dateMap.values()).sort((a, b) => 
      new Date(a.date) - new Date(b.date)
    );
  };

  const downloadCSV = () => {
    if (!data) return;
    
    let csv = 'Date,Currency,Rate\n';
    data.data.forEach(currency => {
      currency.dates.forEach((date, idx) => {
        csv += `${date},${currency.currency},${currency.rates[idx]}\n`;
      });
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `exchange_rates_${startDate}_to_${endDate}.csv`;
    a.click();
  };

  const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-2">
            <DollarSign className="w-10 h-10 text-indigo-600" />
            <h1 className="text-4xl font-bold text-gray-800">Currency Exchange Rate Analyzer</h1>
          </div>
          <p className="text-gray-600">Against the US Dollar (USD)</p>
        </div>

        {/* Data Source Selection */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-indigo-600" />
            Data Source
          </h2>
          <div className="flex gap-4 mb-4">
            <button
              onClick={() => setDataSource('api')}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                dataSource === 'api'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Use API Data
            </button>
            <button
              onClick={() => setDataSource('csv')}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                dataSource === 'csv'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Upload CSV File
            </button>
          </div>

          {/* CSV Upload Section */}
          {dataSource === 'csv' && (
            <div className="bg-blue-50 border-2 border-dashed border-blue-300 rounded-lg p-6">
              <div className="text-center mb-4">
                <Upload className="w-12 h-12 text-blue-600 mx-auto mb-2" />
                <h3 className="font-semibold text-gray-800 mb-2">Upload Exchange Rate CSV</h3>
                <p className="text-sm text-gray-600 mb-4">
                  CSV format: Date, Currency, Rate
                </p>
              </div>
              
              <div className="flex flex-col items-center gap-3">
                <label className="w-full max-w-md">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="hidden"
                    id="csv-upload"
                  />
                  <div className="bg-white border-2 border-gray-300 rounded-lg p-4 cursor-pointer hover:border-indigo-500 transition-colors text-center">
                    {csvFile ? (
                      <div className="flex items-center justify-center gap-2">
                        <CheckCircle className="w-5 h-5 text-green-600" />
                        <span className="text-sm font-medium text-gray-700">{csvFile.name}</span>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">Click to select CSV file</span>
                    )}
                  </div>
                </label>
                
                <button
                  onClick={downloadTemplate}
                  className="text-sm text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1"
                >
                  <Download className="w-4 h-4" />
                  Download CSV Template
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Configuration Panel */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">

          {dataSource === 'api' && (
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-indigo-600" />
            Filters
          </h2>
          )}
                    
          {dataSource === 'api' && (
            // Currency Selection
            <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Select Currencies ({selectedCurrencies.length} selected)
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 max-h-64 overflow-y-auto p-2 border rounded-lg">
              {currencies && Object.keys(currencies).length > 0 ? (
                Object.entries(currencies).map(([code, name]) => (
                  <label key={code} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedCurrencies.includes(code)}
                      onChange={() => handleCurrencyToggle(code)}
                      className="w-4 h-4 text-indigo-600 rounded"
                    />
                    <span className="text-sm font-medium">{code}</span>
                    <span className="text-xs text-gray-500 truncate">{name}</span>
                  </label>
                ))
              ) : (
                <div className="col-span-full text-center text-gray-500 py-4">
                  Loading currencies...
                </div>
              )}
            </div>
          </div>
          )}

          {dataSource === 'api' && (
            // Date Range & Interval
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                min="2008-01-01" 
                max={endDate}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                min={startDate}
                max={new Date().toISOString().split('T')[0]}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Interval</label>
              <select
                value={interval}
                onChange={(e) => setInterval(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                <option value="1d">Daily</option>
                <option value="1wk">Weekly</option>
                <option value="1mo">Monthly</option>
              </select>
            </div>
          </div>
          )}          

          {/* Analyze Button */}
          <button
            onClick={handleAnalyze}
            disabled={loading || selectedCurrencies.length === 0 || (dataSource === 'csv' && !csvFile)}
            className="mt-6 w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader className="w-5 h-5 animate-spin" />
                {dataSource === 'csv' ? 'Uploading & Analyzing...' : 'Analyzing...'}
              </>
            ) : (
              <>
                <TrendingUp className="w-5 h-5" />
                {dataSource === 'csv' ? 'Upload & Analyze CSV' : 'Analyze Exchange Rates'}
              </>
            )}
          </button>
        </div>

        {/* Upload Success Message */}
        {uploadStatus && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <p className="text-green-800">{uploadStatus}</p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-800 font-medium">Error</p>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Results */}
        {data && data.data && (
          <>
            {/* Success Message */}
            {data.message && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <p className="text-green-800">{data.message}</p>
              </div>
            )}

            {/* Warnings */}
            {data.errors && data.errors.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                <p className="text-yellow-800 font-medium mb-2">Some currencies failed to load:</p>
                <ul className="text-yellow-700 text-sm list-disc list-inside">
                  {data.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Performance Summary */}
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Performance Summary</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {data.data.map((currency, idx) => {
                  const isPositive = currency.percentage_change >= 0;
                  return (
                    <div key={currency.currency} className="bg-gray-50 rounded-lg p-4 border-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-bold text-lg">{currency.currency}</h3>
                        <div className={`flex items-center gap-1 ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                          {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                          <span className="font-semibold">{currency.percentage_change >= 0 ? '+' : ''}{currency.percentage_change}%</span>
                        </div>
                      </div>
                      <div className="text-2xl font-bold text-gray-800 mb-2">
                        {currency.end_rate.toFixed(4)}
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        <div className="flex justify-between">
                          <span>Min:</span>
                          <span className="font-medium">{currency.min_rate.toFixed(4)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Max:</span>
                          <span className="font-medium">{currency.max_rate.toFixed(4)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Chart */}
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Exchange Rate Trends</h2>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={formatChartData()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fontSize: 12 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                  />
                  <Legend />
                  {data.data.map((currency, idx) => (
                    <Line
                      key={currency.currency}
                      type="monotone"
                      dataKey={currency.currency}
                      stroke={colors[idx % colors.length]}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Statistics Table */}
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Detailed Statistics</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b">
                      <th className="px-4 py-3 text-left font-semibold">Currency</th>
                      <th className="px-4 py-3 text-right font-semibold">Start Rate</th>
                      <th className="px-4 py-3 text-right font-semibold">End Rate</th>
                      <th className="px-4 py-3 text-right font-semibold">Change (%)</th>
                      <th className="px-4 py-3 text-right font-semibold">Min Rate</th>
                      <th className="px-4 py-3 text-right font-semibold">Max Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.data.map((currency, idx) => {
                      const isPositive = currency.percentage_change >= 0;
                      return (
                        <tr key={currency.currency} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium">{currency.currency}</td>
                          <td className="px-4 py-3 text-right">{currency.start_rate.toFixed(4)}</td>
                          <td className="px-4 py-3 text-right">{currency.end_rate.toFixed(4)}</td>
                          <td className={`px-4 py-3 text-right font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                            {currency.percentage_change >= 0 ? '+' : ''}{currency.percentage_change}%
                          </td>
                          <td className="px-4 py-3 text-right">{currency.min_rate.toFixed(4)}</td>
                          <td className="px-4 py-3 text-right">{currency.max_rate.toFixed(4)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Download Button */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Export Data</h2>
              <button
                onClick={downloadCSV}
                className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors flex items-center gap-2"
              >
                <Download className="w-5 h-5" />
                Download as CSV
              </button>
            </div>
          </>
        )}

        {/* Footer */}
        <div className="text-center mt-8 text-gray-600 text-sm">
          <p>Currency Exchange Rate Analyzer</p>
        </div>
      </div>
    </div>
  );
}