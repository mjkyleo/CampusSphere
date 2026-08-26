const http = require('http');
http.get({host:'localhost', port:5173, path:'/index.css'}, (res) => {
  let data = '';
  res.on('data', c => data += c);
  res.on('end', () => {
    const re = /\.[a-zA-Z][\w:\\/\[\].-]*(?=[\s{,])/g;
    const all = new Set();
    let m;
    while ((m = re.exec(data)) !== null) all.add(m[0].trim());
    console.log('total selectors:', all.size);
    console.log('first 60:', [...all].slice(0, 60).join(' | '));
    console.log('lg selectors:', [...all].filter(s => s.startsWith('.lg')).slice(0, 30).join(' | '));
    console.log('has .fixed:', [...all].some(s => s.endsWith('.fixed')));
    console.log('has .flex:', [...all].some(s => s.endsWith('.flex')));
    console.log('has .min-h-screen:', [...all].some(s => s.endsWith('.min-h-screen')));
    console.log('has .py-2\\\\.5:', [...all].some(s => s.endsWith('.py-2\\.5')));
    console.log('has .backdrop-blur-md:', [...all].some(s => s.endsWith('.backdrop-blur-md')));
    console.log('has .lg\\\\:flex:', [...all].some(s => s === '.lg\\:flex'));
    console.log('has .lg\\\\:top-0:', [...all].some(s => s === '.lg\\:top-0'));
  });
});
