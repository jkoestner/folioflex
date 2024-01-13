import React, { useEffect, useState } from 'react';
import { Link, RouteComponentProps } from 'react-router-dom';
import NavigationLink from 'plaid-threads/NavigationLink';
import LoadingSpinner from 'plaid-threads/LoadingSpinner';

import { TransactionType } from './types';
import { useTransactions } from '../services';
import { setLabel } from '../services/api';

import { LoadingCallout, ErrorMessage } from '.';

// This page will focus solely on transactions for a user

const TransactionsPage = ({
  match,
}: RouteComponentProps<{ userId: string }>) => {
  const [userTransactions, setUserTransactions] = useState<TransactionType[]>(
    []
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const transactionsPerPage = 50;

  const { getTransactionsByUser, transactionsByUser } = useTransactions();
  const userId = Number(match.params.userId);

  useEffect(() => {
    // Initiates the fetching of transactions for the given user
    getTransactionsByUser(userId);
  }, [getTransactionsByUser, userId]);

  useEffect(() => {
    // fetches the transactions for the given user
    const fetchedTransactions = transactionsByUser[userId];
    if (fetchedTransactions) {
      if (fetchedTransactions.length > 0) {
        const sortedTransactions = [...fetchedTransactions].sort((a, b) => {
          // Type assertions
          const dateA = new Date(a.date as string);
          const dateB = new Date(b.date as string);
          return dateB.getTime() - dateA.getTime();
        });
        setUserTransactions(sortedTransactions);
      } else {
        setError('No transactions found.');
      }
    }
    setIsLoading(false);
  }, [transactionsByUser, userId]);

  // Calculate the visible transactions for the current page
  const indexOfLastTransaction = (currentPage + 1) * transactionsPerPage;
  const indexOfFirstTransaction = indexOfLastTransaction - transactionsPerPage;
  const currentTransactions = userTransactions.slice(
    indexOfFirstTransaction,
    indexOfLastTransaction
  );

  // Pagination
  const paginate = (pageNumber: number) => setCurrentPage(pageNumber);
  const totalPages = Math.ceil(userTransactions.length / transactionsPerPage);
  const pageNumbers = Array.from({ length: totalPages }, (_, i) => i + 1);

  // Label Change Handler
  const handleLabelChange = async (id: number, newLabel: string) => {
    try {
      await setLabel(id, newLabel); // Assuming this is your API call
      setUserTransactions(prevTransactions =>
        prevTransactions.map(transaction =>
          transaction.id === id
            ? { ...transaction, label: newLabel }
            : transaction
        )
      );
    } catch (error) {
      console.error('Error updating label:', error);
    }
  };
  const debounce = <T extends any[]>(
    func: (...args: T) => void,
    delay: number
  ) => {
    let inDebounce: NodeJS.Timeout | undefined;

    return (...args: T) => {
      if (inDebounce) {
        clearTimeout(inDebounce);
      }
      inDebounce = setTimeout(() => func(...args), delay);
    };
  };
  const debouncedLabelUpdate = debounce(handleLabelChange, 500); // 500 ms delay

  return (
    <div>
      <NavigationLink component={Link} to="/">
        BACK TO LOGIN
      </NavigationLink>
      <p />
      <NavigationLink component={Link} to={`/user/${userId}`}>
        USER SUMMARY
      </NavigationLink>

      <h1>User Transactions for ID: {userId}</h1>
      {isLoading ? (
        <div className="loading">
          <LoadingSpinner />
          <LoadingCallout />
        </div>
      ) : error ? (
        <ErrorMessage /> // Assuming ErrorMessage takes a 'message' prop
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Account</th>
                <th>Amount</th>
                <th>Label</th>
                {/* Add other headers as needed */}
              </tr>
            </thead>
            <tbody>
              {currentTransactions.map((
                transaction // Use currentTransactions here
              ) => (
                <tr key={transaction.id}>
                  <td>{transaction.date.slice(0, 10)}</td>
                  <td>{transaction.name}</td>
                  <td>{transaction.account_id}</td>
                  <td>{transaction.amount}</td>
                  <td>
                    <input
                      type="text"
                      value={transaction.label}
                      onChange={e =>
                        debouncedLabelUpdate(transaction.id, e.target.value)
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination">
            {pageNumbers.map(number => (
              <button
                key={number}
                onClick={() => paginate(number - 1)}
                disabled={currentPage === number - 1}
              >
                {number}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default TransactionsPage;
