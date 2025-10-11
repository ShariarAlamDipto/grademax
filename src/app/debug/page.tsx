"use client"
import { useEffect, useState } from 'react'

interface Subject {
  id: string
  code: string
  name: string
  level: string
}

interface Topic {
  id: string
  code: string
  name: string
}

export default function DebugPage() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [topics, setTopics] = useState<Topic[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/subjects')
      .then(r => r.json())
      .then(data => {
        console.log('Subjects:', data)
        setSubjects(data)
      })
      .catch(err => {
        console.error('Subjects error:', err)
        setError(err.message)
      })
  }, [])

  useEffect(() => {
    if (subjects.length > 0) {
      const firstSubject = subjects[0]
      fetch(`/api/topics?subjectId=${firstSubject.id}`)
        .then(r => r.json())
        .then(data => {
          console.log('Topics:', data)
          setTopics(data)
        })
        .catch(err => {
          console.error('Topics error:', err)
          setError(err.message)
        })
    }
  }, [subjects])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Debug Page</h1>
      
      {error && (
        <div className="bg-red-100 text-red-800 p-4 rounded mb-4">
          Error: {error}
        </div>
      )}
      
      <div className="mb-8">
        <h2 className="text-xl font-bold mb-2">Subjects ({subjects.length})</h2>
        <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
          {JSON.stringify(subjects, null, 2)}
        </pre>
      </div>
      
      <div>
        <h2 className="text-xl font-bold mb-2">Topics ({topics.length})</h2>
        <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
          {JSON.stringify(topics, null, 2)}
        </pre>
      </div>
    </div>
  )
}
